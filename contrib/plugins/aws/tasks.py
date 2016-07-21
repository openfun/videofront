from time import sleep, time

from botocore.exceptions import ClientError
from celery import shared_task
from django.conf import settings

from pipeline.videoupload import VideoNotUploaded
from .client import s3_client
from .utils import get_video_key

@shared_task(name='monitor_upload')
def monitor_upload(video_id, until):
    s3 = s3_client()
    bucket = settings.S3_STORAGE_BUCKET
    key = get_video_key(video_id)

    # Wait until the object becomes available
    while True:
        try:
            s3.head_object(
                Bucket=bucket,
                Key=key,
            )
            break
        except ClientError:
            # It is important to check the time after the first call to head_object
            # in order to handle cases when the celery job was started after the
            # file was finished uploading.
            if time() > until:
                # Note that it is a perfectly viable scenario when an upload
                # url is generated and it not used; also, when a user
                # connection drops during upload.
                raise VideoNotUploaded
            sleep(5)

    return bucket, key

@shared_task(name='start_transcoding')
def start_transcoding(bucket, key):
    print "start transcoding", bucket, key

@shared_task(name='monitor_transcoding')
def monitor_transcoding():
    # TODO
    pass
