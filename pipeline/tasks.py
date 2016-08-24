import logging

from django.db.transaction import TransactionManagementError
from django.contrib.auth.models import User
from django.core.cache import cache
from django.utils.timezone import now
from celery import shared_task
import pycaption

from videofront.celery_videofront import send_task
from . import backend
from . import exceptions
from . import models


logger = logging.getLogger(__name__)


def acquire_lock(name, expires_in=None):
    """
    Acquire a database lock. Raises LockUnavailable when the lock is unavailable.
    """
    if cache.add(name, True, timeout=expires_in):
        return True
    raise exceptions.LockUnavailable(name)

def release_lock(name):
    # Note that in unit tests, and in case the wrapped code raises an
    # IntegrityError, releasing the cache will result in a
    # TransactionManagementError. This is because unit tests run inside atomic
    # blocks. We cannot execute queries inside an atomic block if a transaction
    # needs to be rollbacked.
    try:
        cache.delete(name)
    except TransactionManagementError:
        logger.error("Could not release lock %s", name)

def create_upload_url(user_id, filename, playlist_public_id=None):
    """
    Create an unused video upload url.

    Returns: {
        'url' (str): url on which the video file can be sent
        'method': 'GET', 'POST' or 'PUT'
        'expires_at': timestamp at which the url will expire
        'id': public video id
    }
    """
    user = User.objects.get(id=user_id)
    upload_url = backend.get().create_upload_url(filename)

    public_video_id = upload_url["id"]
    expires_at = upload_url['expires_at']

    playlist = None
    if playlist_public_id is not None:
        playlist = models.Playlist.objects.get(public_id=playlist_public_id)

    models.VideoUploadUrl.objects.create(
        public_video_id=public_video_id,
        expires_at=expires_at,
        filename=filename,
        owner=user,
        playlist=playlist,
    )

    return upload_url

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
            backend.get().get_uploaded_video(upload_url.public_video_id)
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
            owner=upload_url.owner
        )
        video.title = upload_url.filename
        video.save()
        if upload_url.playlist:
            video.playlists.add(upload_url.playlist)

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
    This function is not thread-safe. It should only be called by the transcode_video task.
    """
    video = models.Video.objects.get(public_id=public_video_id)
    # Here We use get_or_create instead of create in order to be able to restart the transcoding job.
    video_transcoding, _created = models.VideoTranscoding.objects.get_or_create(video=video)
    video_transcoding.progress = 0
    video_transcoding.status = models.VideoTranscoding.STATUS_PENDING
    video_transcoding.started_at = now()
    video_transcoding.save()

    jobs = backend.get().create_transcoding_jobs(public_video_id)
    success_job_indexes = []
    error_job_indexes = []
    errors = []
    jobs_progress = [0] * len(jobs)
    while len(success_job_indexes) + len(error_job_indexes) < len(jobs):
        for job_index, job in enumerate(jobs):
            if job_index not in success_job_indexes and job_index not in error_job_indexes:
                try:
                    jobs_progress[job_index], finished = backend.get().get_transcoding_job_progress(job)
                    if finished:
                        success_job_indexes.append(job_index)
                except exceptions.TranscodingFailed as e:
                    error_job_indexes.append(job_index)
                    error_message = e.args[0] if e.args else ""
                    errors.append(error_message)

        video_transcoding.progress = sum(jobs_progress) * 1. / len(jobs)
        video_transcoding.status = models.VideoTranscoding.STATUS_PROCESSING
        video_transcoding.save()

    video_transcoding.message = "\n".join(errors)
    models.VideoFormat.objects.filter(video=video).delete()
    if errors:
        # In case of errors, wipe all data
        video_transcoding.status = models.VideoTranscoding.STATUS_FAILED
        video_transcoding.save()
        delete_resources(public_video_id)
    else:
        # Create video formats first so that they are available as soon as the
        # video object becomes available from the API
        for format_name, bitrate in backend.get().iter_available_formats(public_video_id):
            models.VideoFormat.objects.create(video=video, name=format_name, bitrate=bitrate)

        video_transcoding.status = models.VideoTranscoding.STATUS_SUCCESS
        video_transcoding.save()

def upload_subtitle(public_video_id, subtitle_public_id, language_code, content):
    """
    Convert subtitle to VTT and upload it.

    Args:
        public_video_id (str)
        subtitle_id (str)
        language_code (str)
        content (bytes)
    """
    # Note: if this ever raises an exception, we should convert it to SubtitleInvalid
    content = content.decode('utf-8')

    # Convert to VTT, whatever the initial format
    content = content.strip("\ufeff\n\r")
    sub_reader = pycaption.detect_format(content)
    if sub_reader is None:
        raise exceptions.SubtitleInvalid("Could not detect subtitle format")
    if sub_reader != pycaption.WebVTTReader:
        content = pycaption.WebVTTWriter().write(sub_reader().read(content))

    backend.get().upload_subtitle(public_video_id, subtitle_public_id, language_code, content)

def delete_resources(public_video_id):
    """ Delete all video assets """
    backend.get().delete_resources(public_video_id)

def delete_subtitle(public_video_id, public_subtitle_id):
    """ Delete subtitle associated to video"""
    backend.get().delete_subtitle(public_video_id, public_subtitle_id)
