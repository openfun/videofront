from botocore.exceptions import ClientError
from django.conf import settings
from django.core.management.base import BaseCommand

from contrib.plugins.aws.client import s3_client


class Command(BaseCommand):
    help = 'Bootstrap S3 for video file storage'

    def handle(self, *args, **options):
        # Create necessay bucket
        s3 = s3_client()

        try:
            s3.head_bucket(Bucket=settings.S3_STORAGE_BUCKET)
            self.stdout.write("Bucket {} already exists".format(settings.S3_STORAGE_BUCKET))
        except ClientError:
            self.stdout.write("Creating bucket {}...".format(settings.S3_STORAGE_BUCKET))
            s3.create_bucket(
                ACL='private',
                Bucket=settings.S3_STORAGE_BUCKET,
                CreateBucketConfiguration={
                    'LocationConstraint': settings.AWS_REGION
                }
            )
