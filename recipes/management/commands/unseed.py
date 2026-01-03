from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from recipes.models import User

class Command(BaseCommand):
    """
    Management command to remove (unseed) user data from the database.

    This command deletes all non-staff users from the database. It is designed
    to complement the corresponding "seed" command, allowing developers to
    reset the database to a clean state without removing administrative users.

    Attributes:
        help (str): Short description displayed when running
            `python manage.py help unseed`.
    """
    
    help = 'Removes seeded sample data'

    def handle(self, *args, **options):
        """
        Execute the unseeding process.

        Deletes all `User` records where `is_staff` is False, preserving
        administrative accounts. Prints a confirmation message upon completion.

        Args:
            *args: Positional arguments passed by Django (not used here).
            **options: Keyword arguments passed by Django (not used here).

        Returns:
            None
        """

        non_staff_users = User.objects.filter(is_staff=False)

        with transaction.atomic():
            # Legacy "follows" table is unmanaged, so delete dependent rows manually
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    DELETE FROM follows
                    WHERE author_id IN (SELECT id FROM recipes_user WHERE is_staff = 0)
                       OR followee_id IN (SELECT id FROM recipes_user WHERE is_staff = 0)
                    """
                )

            deleted_count, _ = non_staff_users.delete()

        self.stdout.write(self.style.SUCCESS(f"Deleted {deleted_count} non-staff users and related data."))
