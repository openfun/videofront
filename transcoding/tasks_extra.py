"""
These functions miror what's done on pipeline.tasks.
The difference is that we don't run the initial transciding,
but instead, we are adding an extra video format.

- We don't delete information from the databse.
- We trigger an extra transcoding and add support for it.
- There is no need to generate thumbnail, since it's supposed
  to be done during the initial transcoding.
"""
from django.utils.timezone import now

from pipeline import exceptions
from pipeline import models
from pipeline.tasks import Lock
from transcoding.backend_extra import AwsExtraBackend


def apply_new_transcoding(public_video_id):
    """
    Args:
        public_video_id (str)
    """
    with Lock("TASK_LOCK_TRANSCODE_VIDEO:" + public_video_id, 3600) as lock:
        if lock.is_acquired:
            try:
                models.invalidate_cache(public_video_id)
                _apply_new_transcoding(public_video_id)
            except Exception as e:
                # Store error message
                message = "\n".join([str(arg) for arg in e.args])
                models.ProcessingState.objects.filter(
                    video__public_id=public_video_id
                ).update(status=models.ProcessingState.STATUS_FAILED, message=message)
                raise
            finally:
                models.invalidate_cache(public_video_id)


def _apply_new_transcoding(public_video_id):
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

    jobs = AwsExtraBackend().apply_new_transcoding(public_video_id)
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
                    jobs_progress[
                        job_index
                    ], finished = AwsExtraBackend().check_progress(job)
                    if finished:
                        success_job_indexes.append(job_index)
                except exceptions.TranscodingFailed as e:
                    error_job_indexes.append(job_index)
                    error_message = e.args[0] if e.args else ""
                    errors.append(error_message)

        # Note that we do not delete original assets once transcoding has
        # ended. This is because we want to keep the possibility of restarting
        # the transcoding process.
        processing_state.update(
            progress=sum(jobs_progress) * 1. / len(jobs),
            status=models.ProcessingState.STATUS_PROCESSING,
        )

    # Check status
    processing_state.update(message="\n".join(errors))
    if errors:
        processing_state.update(status=models.ProcessingState.STATUS_FAILED)
    else:
        # Create video formats first so that they are available as soon as the
        # video object becomes available from the API
        for format_name, bitrate in AwsExtraBackend().iter_new_formats(public_video_id):
            models.VideoFormat.objects.create(
                video=video, name=format_name, bitrate=bitrate
            )

        processing_state.update(status=models.ProcessingState.STATUS_SUCCESS)
