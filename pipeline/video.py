from . import models
from . import plugins

# TODO move this to tasks.py
def get_upload_url(filename):
    """
    Obtain a video upload url.

    Returns: same value as `base_get_upload_url`.
    """
    upload_url = plugins.load().get_upload_url(filename)

    public_video_id = upload_url["id"]
    expires_at = upload_url['expires_at']

    models.VideoUploadUrl.objects.create(
        public_video_id=public_video_id,
        expires_at=expires_at,
        filename=filename
    )

    return upload_url
