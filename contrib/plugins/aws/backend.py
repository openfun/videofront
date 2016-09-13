from botocore.exceptions import ClientError
import boto3
from django.conf import settings

import pipeline.backend
from pipeline.exceptions import TranscodingFailed
import pipeline.utils


class Backend(pipeline.backend.BaseBackend):
    VIDEO_FOLDER_KEY_PATTERN = "videos/{video_id}/"
    VIDEO_KEY_PATTERN = VIDEO_FOLDER_KEY_PATTERN + "{resolution}.mp4"
    SUBTITLE_BASE_KEY_PATTERN = VIDEO_FOLDER_KEY_PATTERN + "subs/{subtitle_id}."
    SUBTITLE_KEY_PATTERN = SUBTITLE_BASE_KEY_PATTERN +  "{language}.vtt"

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

    @classmethod
    def get_subtitle_key(cls, video_id, subtitle_id, language):
        return cls.SUBTITLE_KEY_PATTERN.format(video_id=video_id, subtitle_id=subtitle_id, language=language)

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

    def _get_download_base_url(self):
        cloudfront = getattr(settings, 'CLOUDFRONT_DOMAIN_NAME', None)
        if cloudfront:
            # Download from cloudfront
            return "https://{domain}".format(domain=cloudfront)
        else:
            return "https://s3-{region}.amazonaws.com/{bucket}".format(
                region=settings.AWS_REGION,
                bucket=settings.S3_BUCKET,
            )

    ####################
    # Overridden methods
    ####################

    def upload_video(self, public_video_id, file_object):
        """
        Store a video file on S3.
        """
        self.s3_client.put_object(
            ACL='private',
            Body=file_object,
            Bucket=settings.S3_BUCKET,
            Key=self.get_video_folder_key(public_video_id) + 'src/' + file_object.name,
        )

    def start_transcoding(self, public_video_id):
        pipeline_id = settings.ELASTIC_TRANSCODER_PIPELINE_ID
        src_file_key = self.get_src_file_key(public_video_id)

        # Start transcoding jobs
        jobs = []
        for resolution, preset_id, _bitrate in settings.ELASTIC_TRANSCODER_PRESETS:
            output = {
                # Note that the transcoded video should have public-read
                # permissions or be accessible by cloudfront
                'Key': self.get_video_key(public_video_id, resolution),
                'PresetId': preset_id
            }
            # Generate thumbnails
            if preset_id == settings.ELASTIC_TRANSCODER_THUMBNAILS_PRESET:
                output['ThumbnailPattern'] = self.get_video_folder_key(public_video_id) + 'thumbs/{count}'

            job = self.elastictranscoder_client.create_job(
                PipelineId=pipeline_id,
                Input={'Key': src_file_key},
                Output=output
            )
            jobs.append(job['Job'])
        return jobs

    def check_progress(self, job):
        job_id = job['Id']
        job_update = self.elastictranscoder_client.read_job(Id=job_id)
        job_status = job_update['Job']['Output']['Status']
        if job_status == 'Submitted' or job_status == 'Progressing':
            # Elastic Transcoder does not provide any indicator of the time left
            return 0, False
        elif job_status == 'Complete':
            return 100, True
        elif job_status == 'Error':
            error_message = job_update['Job']['Output']['StatusDetail']
            raise TranscodingFailed(error_message)
        else:
            raise TranscodingFailed('Unknown transcoding status: {}'.format(job_status))

    def delete_video(self, public_video_id):
        folder = self.get_video_folder_key(public_video_id)
        self.delete_objects(folder)

    def delete_subtitle(self, public_video_id, public_subtitle_id):
        prefix = self.SUBTITLE_BASE_KEY_PATTERN.format(video_id=public_video_id, subtitle_id=public_subtitle_id)
        self.delete_objects(prefix)

    def delete_objects(self, prefix):
        """
        Recursively delete all objects with the given prefix. This can be used
        to delete an entire folder.
        """
        bucket = settings.S3_BUCKET
        list_objects = self.s3_client.list_objects(Bucket=bucket, Prefix=prefix)
        for obj in list_objects.get('Contents', []):
            self.s3_client.delete_object(
                Bucket=bucket,
                Key=obj['Key']
            )

    def iter_formats(self, public_video_id):
        for resolution, _preset_id, bitrate in settings.ELASTIC_TRANSCODER_PRESETS:
            try:
                self.s3_client.head_object(
                    Bucket=settings.S3_BUCKET,
                    Key=self.get_video_key(public_video_id, resolution)
                )
            except ClientError:
                continue
            yield resolution, bitrate

    def upload_subtitle(self, video_id, subtitle_id, language_code, content):
        self.s3_client.put_object(
            ACL='public-read',
            Body=content,
            Bucket=settings.S3_BUCKET,
            Key=self.get_subtitle_key(video_id, subtitle_id, language_code),
        )

    def video_url(self, public_video_id, format_name):
        return self._get_download_base_url() + '/' + self.VIDEO_KEY_PATTERN.format(
            video_id=public_video_id,
            resolution=format_name,
        )

    def subtitle_url(self, video_id, subtitle_id, language):
        return self._get_download_base_url() + '/' + self.SUBTITLE_KEY_PATTERN.format(
            video_id=video_id,
            subtitle_id=subtitle_id,
            language=language,
        )

    def thumbnail_url(self, video_id):
        # Use the first generated thumbnail as the video thumbnail
        return self._get_download_base_url() + '/' + self.get_video_folder_key(video_id) + 'thumbs/00001.png'
