from .core import app, STATIC_DIR

# Import service modules for their route registration side effects.
from .services import update_service as update_service  # noqa: F401
from .services import history_service as history_service  # noqa: F401
from .services import queue_service as queue_service  # noqa: F401
from .services import provider_service as provider_service  # noqa: F401
from .runninghub import routes as runninghub_routes  # noqa: F401
from .services import image_service as image_service  # noqa: F401
from .services import llm_service as llm_service  # noqa: F401
from .services import video_service as video_service  # noqa: F401
from .services import canvas_service as canvas_service  # noqa: F401

from fastapi.staticfiles import StaticFiles
import os

# Mount static files after API routes are registered.
if os.path.isdir(STATIC_DIR):
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")

__all__ = ["app"]
