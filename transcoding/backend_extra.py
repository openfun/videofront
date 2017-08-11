from botocore.exceptions import ClientError
from django.conf import settings

from contrib.plugins.aws.backend import Backend as AwsBackend


class AwsExtraBackend(AwsBackend):
    '''
    Extends the AWS backend, adding ability to apply a new
    transcoding foramt on top of the existing video formats
    that were initially transcoded.
    '''
    def apply_new_transcoding(self, public_video_id):
        pipeline_id = settings.ELASTIC_TRANSCODER_PIPELINE_ID
        src_file_key = self.get_src_file_key(public_video_id)

        # Start transcoding jobs
        jobs = []
        for resolution, preset_id, _bitrate in settings.ELASTIC_TRANSCODER_NEW_PRESETS:
            output = {
                # Note that the transcoded video should have public-read
                # permissions or be accessible by cloudfront
                'Key': self.get_video_key(public_video_id, resolution),
                'PresetId': preset_id
            }
            job = self.elastictranscoder_client.create_job(
                PipelineId=pipeline_id,
                Input={'Key': src_file_key},
                Output=output
            )
            jobs.append(job['Job'])
        return jobs

    def iter_new_formats(self, public_video_id):
        for resolution, _preset_id, bitrate in settings.ELASTIC_TRANSCODER_NEW_PRESETS:
            try:
                self.s3_client.head_object(
                    Bucket=settings.S3_BUCKET,
                    Key=self.get_video_key(public_video_id, resolution)
                )
            except ClientError:
                continue
            yield resolution, bitrate

