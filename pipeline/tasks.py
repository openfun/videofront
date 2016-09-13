import logging
from time import sleep

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


class Lock(object):
    """
    Lock context manager.

    Usage:

        with Lock('mylockname', timeout=3600) as lock:
            if lock.is_acquired:
                run_not_thread_safe_code()
    """

    def __init__(self, name, timeout=60, wait=False):
        """
        Args:
            name (str)
            timeout (int): lock expiry duration, in seconds. Set to None if the
            lock should not expire (not recommended).
            wait (bool): if True, and if there is a concurrent call to this
            function, it will block until completion of the concurrent task.
            Note, however, that in this case the lock will *not* be acquired.
        """
        self.name = name
        self.timeout = timeout
        self.wait = wait
        self.is_acquired = False

    def __enter__(self):
        try:
            acquire_lock(self.name, expires_in=self.timeout)
            self.is_acquired = True
        except exceptions.LockUnavailable:
            if self.wait:
                while cache.get(self.name) is not None:
                    sleep(0.1)
        return self

    def __exit__(self, exc_t, exc_v, trace):
        if self.is_acquired:
            release_lock(self.name)
            self.is_acquired = False


def acquire_lock(name, expires_in=None):
    """
    Acquire a database lock. Raises LockUnavailable when the lock is unavailable.
    """
    if cache.add(name, True, timeout=expires_in):
        return True
    raise exceptions.LockUnavailable(name)

def release_lock(name):
    """
    Release a lock for all. Note that the lock will be released even if it was
    never acquired.
    """
    # Note that in unit tests, and in case the wrapped code raises an
    # IntegrityError, releasing the cache will result in a
    # TransactionManagementError. This is because unit tests run inside atomic
    # blocks. We cannot execute queries inside an atomic block if a transaction
    # needs to be rollbacked.
    try:
        cache.delete(name)
    except TransactionManagementError:
        logger.error("Could not release lock %s", name)

def upload_video(public_video_id, file_object):
    """
    Store a video file for transcoding.

    Args:
        public_video_id (str)
        file_object (file)
    """
    video_upload_url = models.VideoUploadUrl.objects.get(public_video_id=public_video_id)

    # Upload video
    backend.get().upload_video(public_video_id, file_object)

    # Create video object
    video = models.Video.objects.create(
        public_id=video_upload_url.public_video_id,
        owner=video_upload_url.owner,
        title=file_object.name
    )
    if video_upload_url.playlist:
        video.playlists.add(video_upload_url.playlist)

    # Delete upload url
    models.VideoUploadUrl.objects.filter(public_video_id=public_video_id).update(was_used=True)

    # Start transcoding
    send_task('transcode_video', args=(public_video_id,))


def get_upload_url(user_id, filename, playlist_public_id=None):
    """
    Create an unused video upload url.

    Returns: {
        'url' (str): url on which the video file can be sent
        'method': 'GET', 'POST' or 'PUT'
        'expires_at': timestamp at which the url will expire
        'id': public video id
    }
    """
    # TODO remove this
    user = User.objects.get(id=user_id)
    upload_url = backend.get().get_upload_url(filename)

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
def monitor_uploads():
    """
    Monitor upload urls to check whether there have been successful uploads.

    This task is run periodically by celery to check the state of upload urls.
    """
    # TODO remove this
    for upload_url in models.VideoUploadUrl.objects.should_check():
        # We dispatch the responsibility of checking the urls to different
        # celery tasks because we do not want to choke the main monitor_uploads
        # task, which is not run concurrently. In other words, if there are
        # many upload urls to be checked, the monitor_uploads task should not
        # take a long time to complete. Otherwise, transcoding will take a long
        # time to start.
        send_task('monitor_upload', args=(upload_url.public_video_id,))

@shared_task(name='monitor_upload')
def monitor_upload(public_video_id, wait=False):
    """
    Warning: this function should be thread-safe, since it can be called from an API view.

    Args:
        public_video_id (str)
        wait (bool): if True, and if there is a concurrent call to this
        function, it will block until completion of the concurrent task.
    """
    # TODO remove this
    # This task should not run if there is already another one running
    with Lock('TASK_LOCK_MONITOR_UPLOAD:' + public_video_id, 60, wait=wait) as lock:
        if lock.is_acquired:
            _monitor_upload(public_video_id)
        elif wait:
            lock.wait_until_available()


def _monitor_upload(public_video_id):
    # TODO remove this
    upload_url = models.VideoUploadUrl.objects.get(public_video_id=public_video_id)
    try:
        backend.get().check_video(upload_url.public_video_id)
        upload_url.was_used = True
    except exceptions.VideoNotUploaded:
        # Upload url was not used yet
        return
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

@shared_task(name='transcode_video_restart')
def transcode_video_restart():
    with Lock('TASK_LOCK_TRANSCODE_VIDEO_RESTART', 60) as lock:
        if lock.is_acquired:
            for processing_state in models.ProcessingState.objects.filter(status=models.ProcessingState.STATUS_RESTART):
                send_task('transcode_video', args=(processing_state.video.public_id,), kwargs={'delete': False})

@shared_task(name='transcode_video')
def transcode_video(public_video_id, delete=True):
    """
    Args:
        public_video_id (str)
        delete (bool): delete video on failure
    """
    with Lock('TASK_LOCK_TRANSCODE_VIDEO:' + public_video_id, 3600) as lock:
        if lock.is_acquired:
            try:
                _transcode_video(public_video_id, delete=delete)
            except Exception as e:
                # Store error message
                message = "\n".join(e.args)
                models.ProcessingState.objects.filter(
                    video__public_id=public_video_id
                ).update(
                    status=models.ProcessingState.STATUS_FAILED,
                    message=message,
                )
                raise

def _transcode_video(public_video_id, delete=True):
    """
    This function is not thread-safe. It should only be called by the transcode_video task.
    """
    video = models.Video.objects.get(public_id=public_video_id)
    video.processing_state.progress = 0
    video.processing_state.status = models.ProcessingState.STATUS_PENDING
    video.processing_state.started_at = now()
    video.processing_state.save()

    jobs = backend.get().start_transcoding(public_video_id)
    success_job_indexes = []
    error_job_indexes = []
    errors = []
    jobs_progress = [0] * len(jobs)
    while len(success_job_indexes) + len(error_job_indexes) < len(jobs):
        for job_index, job in enumerate(jobs):
            if job_index not in success_job_indexes and job_index not in error_job_indexes:
                try:
                    jobs_progress[job_index], finished = backend.get().check_progress(job)
                    if finished:
                        success_job_indexes.append(job_index)
                except exceptions.TranscodingFailed as e:
                    error_job_indexes.append(job_index)
                    error_message = e.args[0] if e.args else ""
                    errors.append(error_message)

        video.processing_state.progress = sum(jobs_progress) * 1. / len(jobs)
        video.processing_state.status = models.ProcessingState.STATUS_PROCESSING
        video.processing_state.save()

    video.processing_state.message = "\n".join(errors)
    models.VideoFormat.objects.filter(video=video).delete()
    if errors:
        video.processing_state.status = models.ProcessingState.STATUS_FAILED
        video.processing_state.save()
        if delete:
            # In case of errors, wipe all data
            delete_video(public_video_id)
    else:
        # Create video formats first so that they are available as soon as the
        # video object becomes available from the API
        for format_name, bitrate in backend.get().iter_formats(public_video_id):
            models.VideoFormat.objects.create(video=video, name=format_name, bitrate=bitrate)

        video.processing_state.status = models.ProcessingState.STATUS_SUCCESS
        video.processing_state.save()

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

def delete_video(public_video_id):
    """ Delete all video assets """
    backend.get().delete_video(public_video_id)

def delete_subtitle(public_video_id, public_subtitle_id):
    """ Delete subtitle associated to video"""
    backend.get().delete_subtitle(public_video_id, public_subtitle_id)
