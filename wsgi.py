"""WSGI entrypoint for production servers (e.g. Gunicorn).

Example:
    gunicorn --bind 0.0.0.0:5000 --workers 2 --threads 4 --timeout 120 wsgi:app
"""
from app import app

if __name__ == "__main__":
    app.run()
