from botocore.exceptions import ClientError
from django.conf import settings
from django.core.management.base import BaseCommand

from contrib.plugins.aws.client import s3_client


class Command(BaseCommand):
    help = 'Bootstrap S3 for video file storage'

    def handle(self, *args, **options):
        self.create_bucket(settings.S3_BUCKET, 'private')

    def create_bucket(self, bucket_name, acl):
        s3 = s3_client()
        try:
            s3.head_bucket(Bucket=bucket_name)
            self.stdout.write("Bucket {} already exists".format(bucket_name))
        except ClientError:
            self.stdout.write("Creating bucket {}...".format(bucket_name))
            s3.create_bucket(
                ACL=acl,
                Bucket=bucket_name,
                CreateBucketConfiguration={
                    'LocationConstraint': settings.AWS_REGION
                }
            )
