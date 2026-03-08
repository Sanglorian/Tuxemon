# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
import logging
import time
import warnings

import pytest
from pydantic import BaseModel

from tuxemon.config import LoggingConfig, LoggingConfigModel
from tuxemon.constants import paths


@pytest.fixture
def mock_storage(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "USER_STORAGE_DIR", tmp_path)
    return tmp_path


class FakeFullConfig(BaseModel):
    logging: LoggingConfigModel


@pytest.fixture
def base_model():
    return FakeFullConfig(logging=LoggingConfigModel())


@pytest.fixture(autouse=True)
def reset_logging():
    for logger_name in list(logging.Logger.manager.loggerDict.keys()):
        logger = logging.getLogger(logger_name)
        logger.handlers.clear()
        logger.filters.clear()

    root = logging.getLogger()
    root.handlers.clear()
    root.filters.clear()
    root.setLevel(logging.NOTSET)


@pytest.mark.parametrize(
    "level_str,expected",
    [
        ("debug", logging.DEBUG),
        ("info", logging.INFO),
        ("warning", logging.WARNING),
        ("error", logging.ERROR),
        ("critical", logging.CRITICAL),
        ("unknown", logging.INFO),
    ],
)
def test_log_level_mapping(level_str, expected, base_model, mock_storage):
    base_model.logging.debug_level = level_str
    cfg = LoggingConfig(base_model)
    assert cfg.LOG_LEVELS.get(level_str, logging.INFO) == expected


@pytest.mark.parametrize(
    "loggers_str,expected",
    [
        ("all", ["all"]),
        ("a,b,c", ["a", "b", "c"]),
        (" a,  b ,c ", ["a", "b", "c"]),
        ("", [""]),
    ],
)
def test_logger_list_parsing(loggers_str, expected, base_model, mock_storage):
    base_model.logging.loggers = loggers_str
    cfg = LoggingConfig(base_model)
    assert cfg.loggers == expected


def test_debug_logging_enables_warnings(base_model, mock_storage):
    base_model.logging.debug_logging = True
    with warnings.catch_warnings(record=True) as w:
        cfg = LoggingConfig(base_model)
        cfg.configure()
        warnings.warn("test-warning")
        assert any("test-warning" in str(wi.message) for wi in w)


def test_handlers_added(base_model, mock_storage):
    base_model.logging.loggers = "test_logger"
    cfg = LoggingConfig(base_model)
    cfg.configure()
    logger = logging.getLogger("test_logger")
    handlers = logger.handlers
    assert len(handlers) >= 1
    assert any(isinstance(h, logging.StreamHandler) for h in handlers)


def test_file_logging_creates_directory_and_file(base_model, mock_storage):
    base_model.logging.dump_to_file = True
    base_model.logging.loggers = "test_logger"
    cfg = LoggingConfig(base_model)
    cfg.configure()
    log_dir = mock_storage / "logs"
    assert log_dir.exists()
    assert any(log_dir.glob("*.log"))


def test_file_logging_rotation(base_model, mock_storage):
    base_model.logging.dump_to_file = True
    base_model.logging.file_keep_max = 2
    base_model.logging.loggers = "test_logger"
    log_dir = mock_storage / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    for i in range(5):
        p = log_dir / f"old_{i}.log"
        p.write_text("x")
        time.sleep(0.01)
    cfg = LoggingConfig(base_model)
    cfg.configure()
    remaining = sorted(log_dir.glob("*.log"))
    assert len(remaining) == 2


def test_file_logging_keep_max_zero(base_model, mock_storage):
    base_model.logging.dump_to_file = True
    base_model.logging.file_keep_max = 0
    base_model.logging.loggers = "test_logger"
    log_dir = mock_storage / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    (log_dir / "old.log").write_text("x")
    cfg = LoggingConfig(base_model)
    cfg.configure()
    logs = list(log_dir.glob("*.log"))
    assert len(logs) == 1


def test_all_logger_sets_root_level(base_model, mock_storage):
    base_model.logging.loggers = "all"
    base_model.logging.debug_level = "debug"
    cfg = LoggingConfig(base_model)
    cfg.configure()
    root_logger = logging.getLogger()
    assert root_logger.level == logging.DEBUG


def test_no_auto_configure(base_model, mock_storage):
    base_model.logging.loggers = "test_logger"
    cfg = LoggingConfig(base_model)
    logger = logging.getLogger("test_logger")
    assert logger.handlers == []
    cfg.configure()
    assert logger.handlers != []


def test_no_duplicate_handlers(base_model, mock_storage):
    base_model.logging.loggers = "test_logger"
    cfg = LoggingConfig(base_model)
    cfg.configure()
    logger = logging.getLogger("test_logger")
    initial_count = len(logger.handlers)
    cfg.configure()
    assert len(logger.handlers) == initial_count


def test_pyscroll_logger_forced_error(base_model, mock_storage):
    cfg = LoggingConfig(base_model)
    cfg.configure()
    pyscroll_logger = logging.getLogger("orthographic")
    assert pyscroll_logger.level == logging.ERROR
