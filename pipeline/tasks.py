import logging
from tempfile import NamedTemporaryFile
from time import sleep

from django.core.cache import cache
from django.db.transaction import TransactionManagementError
from django.utils.timezone import now

import pycaption
from celery import shared_task

from videofront.celery_videofront import send_task

from . import backend, exceptions, models, utils

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
    # Make upload url unavailable immediately to avoid race conditions
    models.VideoUploadUrl.objects.filter(public_video_id=public_video_id).update(
        was_used=True
    )

    video_upload_url = models.VideoUploadUrl.objects.get(
        public_video_id=public_video_id
    )

    # Upload video
    backend.get().upload_video(public_video_id, file_object)

    # Create video object
    video = models.Video.objects.create(
        public_id=video_upload_url.public_video_id,
        owner=video_upload_url.owner,
        title=file_object.name,
    )
    if video_upload_url.playlist:
        video.playlists.add(video_upload_url.playlist)

    # Start transcoding
    send_task("transcode_video", args=(public_video_id,))


@shared_task(name="transcode_video_restart")
def transcode_video_restart():
    with Lock("TASK_LOCK_TRANSCODE_VIDEO_RESTART", 60) as lock:
        if lock.is_acquired:
            for processing_state in models.ProcessingState.objects.filter(
                status=models.ProcessingState.STATUS_RESTART
            ):
                send_task(
                    "transcode_video",
                    args=(processing_state.video.public_id,),
                    kwargs={"delete": False},
                )


@shared_task(name="transcode_video")
def transcode_video(public_video_id, delete=True):
    """
    Args:
        public_video_id (str)
        delete (bool): delete video on failure
    """
    with Lock("TASK_LOCK_TRANSCODE_VIDEO:" + public_video_id, 3600) as lock:
        if lock.is_acquired:
            try:
                models.invalidate_cache(public_video_id)
                _transcode_video(public_video_id, delete=delete)
            except Exception as error:
                # Store error message
                message = "\n".join([str(arg) for arg in error.args])
                models.ProcessingState.objects.filter(
                    video__public_id=public_video_id
                ).update(status=models.ProcessingState.STATUS_FAILED, message=message)
                raise
            finally:
                models.invalidate_cache(public_video_id)


def _transcode_video(public_video_id, delete=True):
    """
    This function is not thread-safe. It should only be called by the transcode_video task.
    """
    video = models.Video.objects.get(public_id=public_video_id)
    processing_state = models.ProcessingState.objects.filter(
        video__public_id=public_video_id
    )
    processing_state.update(
        progress=0, status=models.ProcessingState.STATUS_PENDING, started_at=now()
    )

    jobs = backend.get().start_transcoding(public_video_id)
    success_job_indexes = []
    error_job_indexes = []
    errors = []
    jobs_progress = [0] * len(jobs)
    while len(success_job_indexes) + len(error_job_indexes) < len(jobs):
        for job_index, job in enumerate(jobs):
            if (
                job_index not in success_job_indexes
                and job_index not in error_job_indexes
            ):
                try:
                    jobs_progress[job_index], finished = backend.get().check_progress(
                        job
                    )
                    if finished:
                        success_job_indexes.append(job_index)
                except exceptions.TranscodingFailed as error:
                    error_job_indexes.append(job_index)
                    error_message = error.args[0] if error.args else ""
                    errors.append(error_message)

        # Note that we do not delete original assets once transcoding has
        # ended. This is because we want to keep the possibility of restarting
        # the transcoding process.
        processing_state.update(
            progress=sum(jobs_progress) * 1. / len(jobs),
            status=models.ProcessingState.STATUS_PROCESSING,
        )

    # Create thumbnail
    if not errors:
        try:
            backend.get().create_thumbnail(public_video_id, video.public_thumbnail_id)
        except Exception as error:
            error_message = "thumbnail creation: " + error.args[0] if error.args else ""
            errors.append(error_message)

    # Delete related formats (to be re-created)
    models.VideoFormat.objects.filter(video=video).delete()

    # Check status
    processing_state.update(message="\n".join(errors))
    if errors:
        processing_state.update(status=models.ProcessingState.STATUS_FAILED)
        if delete:
            # In case of errors, wipe all data
            delete_video(public_video_id)
    else:
        # Create video formats first so that they are available as soon as the
        # video object becomes available from the API
        for format_name, bitrate in backend.get().iter_formats(public_video_id):
            models.VideoFormat.objects.create(
                video=video, name=format_name, bitrate=bitrate
            )

        processing_state.update(status=models.ProcessingState.STATUS_SUCCESS)

    # If the video was deleted while the file was transcoding, wipe all data
    if not models.Video.objects.filter(public_id=public_video_id).exists():
        delete_video(public_video_id)


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
    content = content.decode("utf-8")

    # Convert to VTT, whatever the initial format
    content = content.strip("\ufeff\n\r")
    sub_reader = pycaption.detect_format(content)
    if sub_reader is None:
        raise exceptions.SubtitleInvalid("Could not detect subtitle format")
    if sub_reader != pycaption.WebVTTReader:
        content = pycaption.WebVTTWriter().write(sub_reader().read(content))

    backend.get().upload_subtitle(
        public_video_id, subtitle_public_id, language_code, content
    )


def upload_thumbnail(public_video_id, file_object):
    """
    Convert thumbnail to jpg and upload it

    Args:
        public_video_id (str)
        content (bytes)
    """
    video = models.Video.objects.get(public_id=public_video_id)
    out_img = NamedTemporaryFile(mode="rb", suffix=".jpg")

    try:
        utils.make_thumbnail(file_object, out_img.name)
    except OSError:
        raise exceptions.ThumbnailInvalid

    # Generate new thumbnail id
    thumb_id = utils.generate_long_random_id()

    # Delete old thumbnail
    backend.get().delete_thumbnail(public_video_id, video.public_thumbnail_id)

    # Upload thumbnail
    backend.get().upload_thumbnail(public_video_id, thumb_id, out_img)

    # Update video properties
    video.public_thumbnail_id = thumb_id
    video.save()


def delete_video(public_video_id):
    """ Delete all video assets """
    backend.get().delete_video(public_video_id)


def delete_subtitle(public_video_id, public_subtitle_id):
    """ Delete subtitle associated to video"""
    backend.get().delete_subtitle(public_video_id, public_subtitle_id)


@shared_task(name="clean_upload_urls")
def clean_upload_urls():
    """
    Remove video upload urls which cannot be used anymore.
    """
    models.VideoUploadUrl.objects.obsolete().delete()
