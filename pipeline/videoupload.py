from celery import chain
from videofront import celery_app
from . import plugins

def base_get_upload_url():
    """
    Return upload urls for uploading video files.

    Returns:
        {
            'url': str,
            'method': 'GET', 'POST' or 'PUT'
        }
        extra: argument that will be passed to the monitor_upload task.
    """
    raise NotImplementedError


class VideoNotUploaded(Exception):
    """
    Raised whenever a video was not uploaded. Note that this may cover upload
    errors, but also cases when an upload url was not used.
    """
    pass


def get_upload_url():
    get_upload_url_plugin = plugins.load("GET_UPLOAD_URL")
    results = get_upload_url_plugin()

    url_info = results[0]
    extra_args = results[1:]

    # Start video upload pipeline
    # TODO handle errors
    # TODO test this
    chain(
        celery_app.tasks['monitor_upload'].s(*extra_args),
        celery_app.tasks['start_transcoding'].s(),
        celery_app.tasks['monitor_transcoding'].s(),
    )

    return url_info
