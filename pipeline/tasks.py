from django.core.cache import cache
from django.utils.timezone import now
from celery import shared_task

from videofront.celery import send_task
from . import exceptions
from . import models
from . import plugins


def acquire_lock(name, expires_in=None):
    """
    Acquire a database lock. Raises LockUnavailable when the lock is unavailable.
    """
    if cache.add(name, True, timeout=expires_in):
        return True
    raise exceptions.LockUnavailable(name)

def release_lock(name):
    cache.delete(name)


@shared_task(name='monitor_uploads')
def monitor_uploads_task():
    # This task should not run if there is already another one running
    lock = 'MONITOR_UPLOADS_TASK_LOCK'
    try:
        acquire_lock(lock, 3600)
    except exceptions.LockUnavailable:
        return

    try:
        monitor_uploads()
    finally:
        release_lock(lock)

def monitor_uploads(public_video_ids=None):
    """
    Monitor upload urls to check whether there have been successful uploads.

    Warning: this function should be thread-safe, since it can be called from an API view.

    Args:
        public_video_ids: if defined, limit search to these videos
    """
    # Check available upload urls
    urls_queryset = models.VideoUploadUrl.objects.should_check()
    if public_video_ids is not None:
        urls_queryset = urls_queryset.filter(public_video_id__in=public_video_ids)
    for upload_url in urls_queryset:
        try:
            plugins.load().get_uploaded_video(upload_url.public_video_id)
            upload_url.was_used = True
        except exceptions.VideoNotUploaded:
            # Upload url was not used yet
            continue
        finally:
            # Notes:
            # - we also modify the last_checked attribute of unused urls
            # - if the last_checked attribute exists, we make sure to set a proper value
            upload_url.last_checked = now() if upload_url.last_checked is None else max(upload_url.last_checked, now())
            upload_url.save()

        # Create corresponding video
        # Here, a get_or_create call is necessary to make sure that this
        # function can run concurrently.
        video, video_created = models.Video.objects.get_or_create(
            public_id=upload_url.public_video_id,
        )
        video.title = upload_url.filename
        video.save()

        # Start transcoding
        if video_created:
            send_task('transcode_video', args=(upload_url.public_video_id,))

@shared_task(name='transcode_video')
def transcode_video(public_video_id):
    lock = 'TRANSCODE_VIDEO:' + public_video_id
    try:
        acquire_lock(lock)
    except exceptions.LockUnavailable:
        return
    try:
        _transcode_video(public_video_id)
    finally:
        release_lock(lock)

def _transcode_video(public_video_id):
    """
    This function is not thread-safe. It should only be run by the transcode_video task.
    """
    # Create video and transcoding objects
    # get_or_create is necessary here, because we want to be able to run
    # transcoding jobs multiple times for the same video (idempotent)
    video, _created = models.Video.objects.get_or_create(public_id=public_video_id)
    video_transcoding, _created = models.VideoTranscoding.objects.get_or_create(video=video)
    video_transcoding.progress = 0
    video_transcoding.status = models.VideoTranscoding.STATUS_PENDING
    video_transcoding.started_at = now()
    video_transcoding.save()

    try:
        for progress in plugins.load().transcode_video(public_video_id):
            video_transcoding.progress = progress
            video_transcoding.status = models.VideoTranscoding.STATUS_PROCESSING
            video_transcoding.save()
    except exceptions.TranscodingFailed as e:
        video_transcoding.status = models.VideoTranscoding.STATUS_FAILED
        video_transcoding.message = e.message
        video_transcoding.save()
        delete_resources(public_video_id)
        return

    video_transcoding.progress = 100
    video_transcoding.status = models.VideoTranscoding.STATUS_SUCCESS
    video_transcoding.save()

def delete_resources(public_video_id):
    # Delete source video and assets
    plugins.load().delete_resources(public_video_id)
