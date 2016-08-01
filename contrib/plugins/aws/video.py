from time import time

from botocore.exceptions import ClientError
from django.conf import settings

from pipeline.utils import generate_video_id
from pipeline.exceptions import VideoNotUploaded, TranscodingFailed

from . import client as aws_client
from .utils import get_video_key, get_video_folder_key


def get_upload_url():
    """
    Generate video upload urls for storage on Amazon S3
    """
    s3 = aws_client.s3_client()
    # TODO we should probably store source files in a private bucket, and
    # transcoded files in a public bucket
    bucket = settings.S3_STORAGE_BUCKET
    video_id = generate_video_id()
    expires_at = time() + 3600
    url = s3.generate_presigned_url(
        'put_object',
        Params={
            'Bucket': bucket,
            'Key': get_video_key(video_id, 'src'),
        },
        ExpiresIn=expires_at - time()
    )

    return {
        'url': url,
        'method': 'PUT',
        'id': video_id,
        'expires_at': expires_at
    }

def get_uploaded_video(public_video_id):
    s3 = aws_client.s3_client()
    bucket = settings.S3_STORAGE_BUCKET
    key = get_video_key(public_video_id, 'src')

    try:
        s3.head_object(
            Bucket=bucket,
            Key=key,
        )
    except ClientError:
        # Note that it is a perfectly viable scenario when an upload
        # url is generated and it not used; also, when a user
        # connection drops during upload.
        raise VideoNotUploaded

def transcode_video(public_video_id):
    # TODO actually start the transcoding job and monitor it
    pipeline_id = settings.ELASTIC_TRANSCODER_PIPELINE_ID

    elastictranscoder = aws_client.elastictranscoder_client()
    jobs = []
    for resolution, preset_id in settings.ELASTIC_TRANSCODER_PRESETS.iteritems():
        job = elastictranscoder.create_job(
            PipelineId=pipeline_id,
            Input={
                'Key': get_video_key(public_video_id, 'src')
            },
            Output={
                'Key': get_video_key(public_video_id, resolution),
                'PresetId': preset_id
            }
        )
        jobs.append(job)

    # Start monitoring jobs
    completed_jobs = []
    error_jobs = []
    error_message = None
    while len(completed_jobs) + len(error_jobs) < len(jobs):
        for job in jobs:
            job_id = job['Job']['Id']
            if job_id not in completed_jobs and job_id not in error_jobs:
                job_update = elastictranscoder.read_job(Id=job_id)
                job_status = job_update['Job']['Output']['Status']
                if job_status == 'Submitted' or job_status == 'Progressing':
                    # Elastic Transcoder does not provide any indicator of the time left
                    pass
                elif job_status == 'Complete':
                    completed_jobs.append(job_id)
                    yield len(completed_jobs) * 100. / len(jobs)
                elif job_status == 'Error':
                    error_message = job_update['Job']['Output']['StatusDetail']
                    error_jobs.append(job_id)
                else:
                    raise TranscodingFailed('Unknown transcoding status: {}'.format(job_status))


    if error_message is not None:
        # We wait until transcoding is over to trigger an error
        raise TranscodingFailed(error_message)


def delete_resources(public_video_id):
    s3 = aws_client.s3_client()
    bucket = settings.S3_STORAGE_BUCKET
    folder = get_video_folder_key(public_video_id)
    for obj in s3.list_objects(Bucket=bucket, prefix=folder)['Contents']:
        s3.delete_object(
            Bucket=bucket,
            Key=obj['Key']
        )
