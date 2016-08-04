from . import models
from . import plugins


def base_get_upload_url():
    """
    Return upload urls for uploading video files.

    Returns:
        {
            'url' (str): url on which the video file can be sent
            'method': 'GET', 'POST' or 'PUT'
            'expires_at': timestamp at which the url will expire
            'id': public video id
        }
    """
    raise NotImplementedError

def base_get_uploaded_video(video_id):
    """
    Get the video file for which an upload url was generated.

    This function is only used to check whether an upload url has been used or not.

    If the upload url has not been used yet, this function should raise a
    VideoNotUploaded exception.

    The return value is not used.
    """
    raise NotImplementedError

def base_transcode_video(video_id):
    """
    Function in charge of running the transcoding job and updating the video
    status in the database.

    This function is an iterator on the task progress. It should periodically
    yield the progress (float value between 0 and 100).
    """
    raise NotImplementedError

def base_delete_resources(video_id):
    """
    Delete all resources associated to a video. E.g: in case of transcoding error.
    """
    raise NotImplementedError


def get_upload_url(filename):
    """
    Obtain a video upload url.

    Returns: same value as `base_get_upload_url`.
    """
    upload_url = plugins.call("GET_UPLOAD_URL", filename)

    public_video_id = upload_url["id"]
    expires_at = upload_url['expires_at']

    models.VideoUploadUrl.objects.create(
        public_video_id=public_video_id,
        expires_at=expires_at,
        filename=filename
    )

    return upload_url
