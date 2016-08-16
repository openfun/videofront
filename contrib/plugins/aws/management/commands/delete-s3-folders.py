from django.core.management.base import BaseCommand

from contrib.plugins.aws.backend import Backend


class Command(BaseCommand):
    help = 'Delete one or more folders on S3'

    def add_arguments(self, parser):
        parser.add_argument('folders', nargs='+', help='Folder names')

    def handle(self, *args, **options):
        backend = Backend()
        for folder in options['folders']:
            backend.delete_folder(folder)
