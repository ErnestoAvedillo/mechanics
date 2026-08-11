#!/bin/bash

python manage.py compilemessages
python manage.py collectstatic --noinput
python manage.py migrate --noinput
if [ "$DJANGO_DEBUG" = "True" ];
then
    echo "Ejecutando Django en modo DESARROLLO (runserver)"
    python manage.py runserver 0.0.0.0:8000
else
    echo "Ejecutando Django en modo PRODUCCION (gunicorn)"
    gunicorn mechanics.wsgi:application --bind 0.0.0.0:8000 --workers=4 --timeout=300
fi

