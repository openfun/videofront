from django.test import TestCase
from django.test.utils import override_settings

from mock import Mock, patch

from contrib.plugins.aws import video as aws_video
import pipeline.exceptions
import pipeline.video
from pipeline.tests.utils import override_plugins
from . import utils


@utils.override_s3_settings
class VideoUploadUrlTests(TestCase):

    @patch('contrib.plugins.aws.video.time')
    @patch('contrib.plugins.aws.client.s3_client')
    @patch('contrib.plugins.aws.video.generate_video_id')
    def test_get_upload_url(self, mock_generate_video_id, mock_s3_client, mock_time):
        mock_s3_client.return_value = Mock(
            generate_presigned_url=Mock(return_value="http://someurl")
        )
        mock_generate_video_id.return_value = "someid"
        mock_time.return_value = 0

        upload_url = aws_video.get_upload_url('filename')

        self.assertEqual({
            'method': 'PUT',
            'url': "http://someurl",
            'expires_at': 3600,
            'id': 'someid'
        }, upload_url)

    @override_plugins(GET_UPLOAD_URL='contrib.plugins.aws.video.get_upload_url')
    @patch('contrib.plugins.aws.client.s3_client')
    def test_get_upload_url_compatibility(self, mock_s3_client):
        mock_s3_client.return_value = Mock(
            generate_presigned_url=Mock(return_value="http://someurl")
        )
        upload_url = pipeline.video.get_upload_url('filename')
        self.assertEqual('http://someurl', upload_url['url'])

    @patch('contrib.plugins.aws.client.s3_client')
    def test_get_successfuly_uploaded_video(self, mock_s3_client):
        mock_s3_client.return_value = Mock(list_objects=Mock(return_value={
            "Contents": [
                {'Key': 'videos/key/src/My file.mp4'}
            ]
        }))

        aws_video.get_uploaded_video('key')
        mock_s3_client.return_value.list_objects.assert_called_once_with(
            Bucket='dummys3storagebucket_private', Prefix='videos/key/src/'
        )

    @patch('contrib.plugins.aws.client.s3_client')
    def test_get_uploaded_video_for_not_uploaded_video(self, mock_s3_client):
        mock_s3_client.return_value = Mock(list_objects=Mock(return_value={
            "Contents": []
        }))

        self.assertRaises(pipeline.exceptions.VideoNotUploaded, aws_video.get_uploaded_video, 'key')

    @patch('contrib.plugins.aws.client.s3_client')
    def test_delete_resources_no_content(self, mock_s3_client):
        mock_s3_client.return_value = Mock(list_objects=Mock(return_value={}))
        aws_video.delete_resources('videoid')

        mock_s3_client.return_value.list_objects.assert_any_call(
            Bucket='dummys3storagebucket_private', Prefix='videos/videoid/'
        )


@utils.override_s3_settings
class TranscodeTests(TestCase):

    @override_settings(ELASTIC_TRANSCODER_PIPELINE_ID='pipelineid')
    @override_settings(ELASTIC_TRANSCODER_PRESETS={'SD': 'presetid'})
    @patch('contrib.plugins.aws.client.elastictranscoder_client')
    @patch('contrib.plugins.aws.video.get_src_file_key')
    def test_transcode_video_success(self, mock_get_src_file_key, mock_elastictranscoder_client):
        create_job_fixture = utils.load_json_fixture('elastictranscoder_create_job.json')
        read_job_fixture = utils.load_json_fixture('elastictranscoder_read_job_complete.json')
        mock_elastictranscoder_client.return_value = Mock(
            create_job=Mock(return_value=create_job_fixture),
            read_job=Mock(return_value=read_job_fixture)
        )
        mock_get_src_file_key.return_value = 'videos/videoid/src/Some video file.mpg'

        progress = 0
        for progress in aws_video.transcode_video('videoid'):
            pass

        self.assertEqual(100, progress)
        mock_elastictranscoder_client.return_value.create_job.assert_called_once_with(
            PipelineId='pipelineid',
            Input={'Key': 'videos/videoid/src/Some video file.mpg'},
            Output={'PresetId': 'presetid', 'Key': aws_video.get_video_key('videoid', 'SD')}
        )
        mock_elastictranscoder_client.return_value.read_job.assert_called_once_with(
            Id='jobid' # job id in test fixture
        )
        mock_get_src_file_key.assert_called_once_with('videoid')
