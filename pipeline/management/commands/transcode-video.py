from django.core.management.base import BaseCommand

from videofront.celery_videofront import send_task


class Command(BaseCommand):
    help = 'Force a transcoding task to start.'

    def add_arguments(self, parser):
        parser.add_argument('video_id', help='Public video ID')

    def handle(self, *args, **options):
        public_video_id = options['video_id']
        send_task('transcode_video', args=(public_video_id,))
        self.stdout.write("Done.")
