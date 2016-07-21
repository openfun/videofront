from time import time

from django.conf import settings

from video.utils import generate_video_id

from .client import s3_client
from .utils import get_video_key


def get_upload_url():
    """
    Generate video upload urls for storage on Amazon S3
    """
    s3 = s3_client()
    # TODO we should probably store source files in a private bucket, and
    # transcoded files in a public bucket
    bucket = settings.S3_STORAGE_BUCKET
    video_id = generate_video_id()
    expires_at = time() + 3600
    url = s3.generate_presigned_url(
        'put_object',
        Params={
            'Bucket': bucket,
            'Key': get_video_key(video_id),
            'ExpiresIn': expires_at - time()
        }
    )

    url_info = {
        'url': url,
        'method': 'PUT'
    }

    return url_info, video_id, expires_at
