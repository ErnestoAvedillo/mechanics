all:
	uv run python -m gunicorn --workers 3 --bind unix:gunicorn.sock mechanics.wsgi:application

	
debug:
	uv run python manage.py runserver 0.0.0.0:8000

restart:
	uv run python manage.py collectstic
	uv run gunicorn --reload mechanics.wsgi:application

restart_ctl:
	systemctl daemon-reload
	systemctl restart gunicorn
	systemctl status gunicorn 
