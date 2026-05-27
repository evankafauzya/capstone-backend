"""ASGI entrypoint for production servers (Uvicorn / Gunicorn with the
uvicorn worker class).

Examples:
    # Pure uvicorn (single worker, threadpool handles concurrent sync handlers)
    uvicorn asgi:app --host 0.0.0.0 --port 5000

    # Gunicorn supervising uvicorn workers (process-level reloads + logs)
    gunicorn --bind 0.0.0.0:5000 --workers 1 \\
             --worker-class uvicorn.workers.UvicornWorker asgi:app

Note: keep ``--workers 1``. Each worker loads PyTorch + MediaPipe + YOLO
into memory; running multiple workers multiplies model RAM. FastAPI runs
sync route handlers on a thread pool, so a single worker still handles
concurrent requests.
"""
from app import app

__all__ = ["app"]
