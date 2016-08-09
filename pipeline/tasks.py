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
    Args:
        public_video_ids: if defined, limit search to these videos
    """
    # Check available upload urls
    urls_queryset = models.VideoUploadUrl.objects.should_check()
    if public_video_ids is not None:
        urls_queryset = urls_queryset.filter(public_video_id__in=public_video_ids)
    for upload_url in urls_queryset:
        try:
            plugins.call('GET_UPLOADED_VIDEO', upload_url.public_video_id)
        except exceptions.VideoNotUploaded:
            # Upload url was not used yet
            continue

        # Mark upload url as used
        upload_url.was_used = True
        upload_url.save()

        # Create corresponding video
        models.Video.objects.create(
            public_id=upload_url.public_video_id,
            title=upload_url.filename,
        )

        # Start transcoding
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
        for progress in plugins.call('TRANSCODE_VIDEO', public_video_id):
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
    plugins.call('DELETE_RESOURCES', public_video_id)
