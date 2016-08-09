from time import time

import boto3
from django.conf import settings

import pipeline.backend
from pipeline.exceptions import VideoNotUploaded, TranscodingFailed
import pipeline.utils


class Backend(pipeline.backend.BaseBackend):
    VIDEO_FOLDER_KEY_PATTERN = "videos/{video_id}/"
    VIDEO_KEY_PATTERN = VIDEO_FOLDER_KEY_PATTERN + "{resolution}.mp4"

    def __init__(self):
        self._session = None
        self._s3_client = None
        self._elastictranscoder_client = None

    @property
    def session(self):
        """
        Boto3 authenticated session
        """
        if self._session is None:
            self._session = boto3.Session(
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
            )
        return self._session

    @property
    def s3_client(self):
        if self._s3_client is None:
            self._s3_client = self.session.client('s3', region_name=settings.AWS_REGION)
        return self._s3_client

    @property
    def elastictranscoder_client(self):
        if self._elastictranscoder_client is None:
            self._elastictranscoder_client = self.session.client('elastictranscoder', region_name=settings.AWS_REGION)
        return self._elastictranscoder_client

    @classmethod
    def get_video_folder_key(cls, video_id):
        """
        Get the S3 folder key associated to this video.
        """
        return cls.VIDEO_FOLDER_KEY_PATTERN.format(video_id=video_id)

    @classmethod
    def get_video_key(cls, video_id, resolution):
        """
        Get the S3 object key associated to this video with the given resolution.
        """
        return cls.VIDEO_KEY_PATTERN.format(video_id=video_id, resolution=resolution)

    def get_src_file_key(self, public_video_id):
        """
        List objects in the video src folder in order to find the key associated to
        the source file. The key depends on the original file name, which we don't
        know.

        Returns None if no source file exists.
        """
        bucket = settings.S3_BUCKET
        src_folder_key = self.get_video_folder_key(public_video_id) + 'src/'
        objects = self.s3_client.list_objects(Bucket=bucket, Prefix=src_folder_key)
        if objects.get('Contents'):
            return objects['Contents'][0]['Key']
        return None

    ####################
    # Overridden methods
    ####################

    def create_upload_url(self, filename):
        """
        Generate video upload urls for storage on Amazon S3
        """
        bucket = settings.S3_BUCKET
        video_id = pipeline.utils.generate_video_id()
        expires_at = time() + 3600
        url = self.s3_client.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': bucket,
                'Key': self.get_video_folder_key(video_id) + 'src/' + filename,
            },
            ExpiresIn=expires_at - time()
        )

        return {
            'url': url,
            'method': 'PUT',
            'id': video_id,
            'expires_at': expires_at
        }

    def get_uploaded_video(self, public_video_id):
        # List content of 'src' folder
        key = self.get_src_file_key(public_video_id)
        if key is None:
            # Note that it is a perfectly viable scenario when an upload
            # url is generated and it not used; also, when a user
            # connection drops during upload.
            raise VideoNotUploaded

    def transcode_video(self, public_video_id):
        pipeline_id = settings.ELASTIC_TRANSCODER_PIPELINE_ID

        # Start transcoding jobs
        jobs = []
        src_file_key = self.get_src_file_key(public_video_id)
        for resolution, preset_id in settings.ELASTIC_TRANSCODER_PRESETS.items():
            job = self.elastictranscoder_client.create_job(
                PipelineId=pipeline_id,
                Input={'Key': src_file_key},
                Output={
                    # Note that the transcoded video should be in the public bucket
                    'Key': self.get_video_key(public_video_id, resolution),
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
                    job_update = self.elastictranscoder_client.read_job(Id=job_id)
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

    def delete_resources(self, public_video_id):
        bucket = settings.S3_BUCKET
        folder = self.get_video_folder_key(public_video_id)
        list_objects = self.s3_client.list_objects(Bucket=bucket, Prefix=folder)
        for obj in list_objects.get('Contents', []):
            self.s3_client.delete_object(
                Bucket=bucket,
                Key=obj['Key']
            )
