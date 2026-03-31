all:
	uv run gunicorn --workers 3 --bind 0.0.0.0:8000 ernestoavedillo.wsgi
debug:
	uv run python manage.py runserver 0.0.0.0:8000
