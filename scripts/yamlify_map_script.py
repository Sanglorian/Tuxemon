"""
Move the events out of a TMX map file and into a YAML file.

* the YAML file will have the same name as the map (``map.tmx`` -> ``map.yaml``)
* the event/interact objects are removed from the TMX, and any object group
  that is left empty as a result (e.g. the "Events" group) is removed too

This matches the layout of the maps that have already been converted: the
events live in a sibling YAML file, and the TMX only keeps the tile layers and
collision regions.

Run this script with one or more files as the argument(s).  YAML files will be
generated in the same folder with the same name as the map and will contain
the event data.

By default the script both writes the YAML *and* strips the events from the
TMX.  Pass ``--keep-tmx`` to only extract the YAML and leave the TMX untouched.

The TMX is edited as text (not re-serialised through ElementTree) so the rest
of the file keeps its exact original formatting and the diff stays minimal.

USAGE

python yamlify_map_script.py [--keep-tmx] FILE0 FILE1 FILE2 ...

You can run the script like this:

    python3 scripts/yamlify_map_script.py mods/tuxemon/maps/map.tmx
"""

import logging
import re
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path
from typing import Any
from xml.etree.ElementTree import Element

from tuxemon.database.yaml_utils import dump_yaml_io, load_yaml

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__file__)


def renumber_event(event_node: Element) -> defaultdict[Any, list]:
    groups = (
        ("act", []),
        ("cond", []),
        ("behav", []),
    )

    for node in event_node:
        item = node.attrib["name"], node.attrib["value"]
        for tag, items in groups:
            if item[0].startswith(tag):
                items.append(item)
                break
        else:
            raise ValueError(node.attrib)

    children = defaultdict(list)
    for tag, items in groups:
        items.sort()
        for item in items:
            index, value = item
            children[tag].append(value)

    return children


# Matches a single <object ... type="event"/"interact" ...> element, whether it
# is self-closing (<object .../>) or has a <properties> child block.  The match
# greedily eats the leading indentation and the trailing newline so removing it
# leaves no blank line behind.
_EVENT_OBJECT_RE = re.compile(
    r'[ \t]*<object\b[^>]*?\btype="(?:event|interact|init)"'
    r"[^>]*?(?:/>|>.*?</object>)[ \t]*\r?\n",
    re.DOTALL,
)

# Matches an <objectgroup> that has no <object> children left (it may still
# contain a <properties> block).  Used to delete the now-empty events group.
_EMPTY_OBJECTGROUP_RE = re.compile(
    r"[ \t]*<objectgroup\b[^>]*>\s*"
    r"(?:<properties>.*?</properties>\s*)?"
    r"</objectgroup>[ \t]*\r?\n",
    re.DOTALL,
)


def strip_events_from_tmx(filename: Path) -> int:
    """
    Remove all event/interact objects from a TMX file, then drop any object
    group that is left empty.  The file is edited as text so the rest of the
    map keeps its exact original formatting.

    Returns:
        The number of event/interact objects removed.
    """
    text = filename.read_text(encoding="utf-8")
    text, removed = _EVENT_OBJECT_RE.subn("", text)
    if removed:
        text = _EMPTY_OBJECTGROUP_RE.sub("", text)
        filename.write_text(text, encoding="utf-8")
    return removed


def extract_events(filename: Path, strip_tmx: bool = True) -> None:
    tree = ET.parse(filename)
    root = tree.getroot()
    yaml_filename = filename.with_suffix(".yaml")

    try:
        yaml_doc = load_yaml(yaml_filename)
    except FileNotFoundError:
        yaml_doc = {"events": {}}

    mapping = (
        ("conditions", "cond"),
        ("actions", "act"),
        ("behav", "behav"),
    )

    tw = int(root.get("tilewidth"))
    th = int(root.get("tileheight"))

    def process_event(obj: Element) -> None:
        event_node = {}

        event_node["x"] = int(obj.attrib.get("x", "0")) // tw
        event_node["y"] = int(obj.attrib.get("y", "0")) // th

        # The loader defaults width/height to 1 tile, so only record them when
        # they differ.  This keeps converted maps consistent with the ones that
        # have already been split out.
        width = int(obj.attrib.get("width", str(tw))) // tw
        height = int(obj.attrib.get("height", str(th))) // th
        if width != 1:
            event_node["width"] = width
        if height != 1:
            event_node["height"] = height

        event_node["type"] = obj.attrib.get("type", "event")

        properties = obj.find("properties")
        if properties is not None and len(properties) > 0:
            children = renumber_event(properties)
            for cname, tname in mapping:
                if tname in children:
                    event_node[cname] = children.pop(tname)
            assert not children

        yaml_doc["events"][obj.attrib["name"]] = event_node

    for event_type in ("interact", "event", "init"):
        for obj in root.findall(f".//object[@type='{event_type}']"):
            process_event(obj)

    with yaml_filename.open("w", encoding="utf-8") as fp:
        dump_yaml_io(
            fp,
            yaml_doc,
            sort_keys=False,
            default_flow_style=False,
        )

    if strip_tmx:
        removed = strip_events_from_tmx(filename)
        logger.info(
            "%s: extracted %d events -> %s, removed %d objects from TMX",
            filename.name,
            len(yaml_doc["events"]),
            yaml_filename.name,
            removed,
        )
    else:
        logger.info(
            "%s: extracted %d events -> %s (TMX left untouched)",
            filename.name,
            len(yaml_doc["events"]),
            yaml_filename.name,
        )


if __name__ == "__main__":
    args = sys.argv[1:]
    strip_tmx = True
    if "--keep-tmx" in args:
        strip_tmx = False
        args = [a for a in args if a != "--keep-tmx"]

    if not args:
        print(
            "USAGE: python yamlify_map_script.py [--keep-tmx] "
            "FILE0 FILE1 FILE2 ..."
        )
        sys.exit(1)

    for filename in args:
        extract_events(Path(filename), strip_tmx=strip_tmx)
