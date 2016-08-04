from time import time

from django.conf import settings

from pipeline.utils import generate_video_id
from pipeline.exceptions import VideoNotUploaded, TranscodingFailed

from . import client as aws_client


VIDEO_FOLDER_KEY_PATTERN = "videos/{video_id}/"
VIDEO_KEY_PATTERN = VIDEO_FOLDER_KEY_PATTERN + "{resolution}.mp4"

def get_video_folder_key(video_id):
    """
    Get the S3 folder key associated to this video.
    """
    return VIDEO_FOLDER_KEY_PATTERN.format(video_id=video_id)

def get_video_key(video_id, resolution):
    """
    Get the S3 object key associated to this video with the given resolution.
    """
    return VIDEO_KEY_PATTERN.format(video_id=video_id, resolution=resolution)

def get_upload_url(filename):
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
            'Key': get_video_folder_key(video_id) + 'src/' + filename,
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
    # List content of 'src' folder
    key = get_src_file_key(public_video_id)
    if key is None:
        # Note that it is a perfectly viable scenario when an upload
        # url is generated and it not used; also, when a user
        # connection drops during upload.
        raise VideoNotUploaded

def transcode_video(public_video_id):
    pipeline_id = settings.ELASTIC_TRANSCODER_PIPELINE_ID
    elastictranscoder = aws_client.elastictranscoder_client()

    # Start transcoding jobs
    jobs = []
    src_file_key = get_src_file_key(public_video_id)
    for resolution, preset_id in settings.ELASTIC_TRANSCODER_PRESETS.iteritems():
        job = elastictranscoder.create_job(
            PipelineId=pipeline_id,
            Input={'Key': src_file_key},
            Output={
                'Key': get_video_key(public_video_id, resolution),
                'PresetId': preset_id
            }
        )
        jobs.append(job)

    # Monitor transcoding jobs
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

def get_src_file_key(public_video_id):
    """
    List objects in the video src folder in order to find the key associated to
    the source file. The key depends on the original file name, which we don't
    know.

    Returns None if no source file exists.
    """
    s3 = aws_client.s3_client()
    bucket = settings.S3_STORAGE_BUCKET
    src_folder_key = get_video_folder_key(public_video_id) + 'src/'
    objects = s3.list_objects(Bucket=bucket, Prefix=src_folder_key)
    if objects.get('Contents'):
        return objects['Contents'][0]['Key']
    return None

def delete_resources(public_video_id):
    s3 = aws_client.s3_client()
    bucket = settings.S3_STORAGE_BUCKET
    folder = get_video_folder_key(public_video_id)
    for obj in s3.list_objects(Bucket=bucket, Prefix=folder)['Contents']:
        s3.delete_object(
            Bucket=bucket,
            Key=obj['Key']
        )
