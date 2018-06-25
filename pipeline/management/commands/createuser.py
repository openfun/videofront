from django.contrib.auth.models import User
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create a user with the given password. If the user already exists, it is updated."

    def add_arguments(self, parser):
        parser.add_argument("--admin", action="store_true", help="Make the user admin")
        parser.add_argument("username", help="Authentication username")
        parser.add_argument("password", help="Authentication password")

    def handle(self, *args, **options):
        username = options["username"]
        password = options["password"]

        user, created = User.objects.get_or_create(username=username)
        user.set_password(password)
        if options.get("admin"):
            user.is_superuser = True
            user.is_staff = True
        user.save()

        self.stdout.write(
            "{} user '{}' with token: {}".format(
                "Created" if created else "Updated", username, user.auth_token.key
            )
        )
