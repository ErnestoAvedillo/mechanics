"""
Deletes the demo users older than a day (see specs/demo.py) together with their library entries.
The shared demo documents belong to another user and are not touched.

  docker exec -w /app/src django python manage.py purge_demo_users
"""
from django.core.management.base import BaseCommand

from specs.demo import expired_demo_users


class Command(BaseCommand):
    help = "Delete expired demo users. / Borra los usuarios de la demo caducados."

    def handle(self, *args, **options):
        users = expired_demo_users()
        total = users.count()
        users.delete()
        self.stdout.write(f"{total} usuarios de demo borrados / {total} demo users deleted")
