from botocore.exceptions import ClientError
from django.conf import settings
from django.core.management.base import BaseCommand

from contrib.plugins.aws.backend import Backend


class Command(BaseCommand):
    help = "Bootstrap S3 for video file storage"

    def handle(self, *args, **options):
        acl = (
            "private" if hasattr(settings, "CLOUDFRONT_DOMAIN_NAME") else "public-read"
        )

        self.create_bucket(settings.S3_BUCKET, acl)
        self.create_bucket(settings.S3_PRIVATE_BUCKET, "private")

    def create_bucket(self, bucket_name, acl):
        backend = Backend()
        try:
            backend.s3_client.head_bucket(Bucket=bucket_name)
            self.stdout.write("Bucket {} already exists".format(bucket_name))
        except ClientError:
            self.stdout.write("Creating bucket {}...".format(bucket_name))
            backend.s3_client.create_bucket(
                ACL=acl,
                Bucket=bucket_name,
                CreateBucketConfiguration={"LocationConstraint": settings.AWS_REGION},
            )
            self.stdout.write("Updating CORS configuration...")
            backend.s3_client.put_bucket_cors(
                Bucket=bucket_name,
                CORSConfiguration={
                    "CORSRules": [
                        {
                            "AllowedHeaders": ["*"],
                            "AllowedMethods": ["GET", "PUT"],
                            "AllowedOrigins": ["*"],
                            "MaxAgeSeconds": 3000,
                        }
                    ]
                },
            )
