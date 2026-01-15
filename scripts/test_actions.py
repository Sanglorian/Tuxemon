"""
Script to validate map actions
"""

from unittest.mock import MagicMock

from tuxemon.constants import paths
from tuxemon.database.runtime import db
from tuxemon.event.eventaction import ActionManager
from tuxemon.event.eventengine import EventEngine
from tuxemon.event.running import ConditionEvaluator
from tuxemon.map.map_loader import TMXMapLoader
from tuxemon.session import Session
from tuxemon.user_config import CONFIG

db.load("monster")
action = ActionManager()
evaluator = ConditionEvaluator(MagicMock(), MagicMock())
engine = EventEngine(Session(), action, evaluator)
loader = TMXMapLoader()
loader.image_loader = MagicMock()

for mod_name in CONFIG.mods:
    for path in (paths.mods_folder / mod_name / "maps").glob("*.tmx"):
        txmn_map = loader.load(str(path))
        for event in txmn_map.events:
            for act in event.acts:
                if not engine.action_manager.get_action(act.type, act.parameters):
                    print(f"{path} failed")
