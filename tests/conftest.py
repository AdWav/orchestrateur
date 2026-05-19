from __future__ import annotations

from importlib import reload

import app.dependencies
import app.main as app_main


def reload_api_app():
    reload(app.dependencies)
    return reload(app_main)
