import os

import pytest


def pytest_configure(config):
    config.addinivalue_line("markers", "slow: minutes-long refits; run with WIKI_SLOW=1")


def pytest_collection_modifyitems(config, items):
    if os.environ.get("WIKI_SLOW") == "1":
        return
    skip = pytest.mark.skip(reason="slow refit; set WIKI_SLOW=1")
    for item in items:
        if "slow" in item.keywords:
            item.add_marker(skip)
