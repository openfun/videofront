from django.test import TestCase
from django.test.utils import override_settings

from mock import Mock, patch

from contrib.plugins.aws import utils as aws_utils
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

        upload_url = aws_video.get_upload_url()

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
        upload_url = pipeline.video.get_upload_url()
        self.assertEqual('http://someurl', upload_url['url'])

    @patch('contrib.plugins.aws.client.s3_client')
    def test_get_uploaded_video_for_uploaded_video(self, mock_s3_client):
        mock_s3_client.return_value = Mock(head_object=Mock(return_value=None))

        # Check no exception is raised
        self.assertIsNone(aws_video.get_uploaded_video('key'))

    @patch('contrib.plugins.aws.client.s3_client')
    def test_get_uploaded_video_for_not_uploaded_video(self, mock_s3_client):
        error = aws_video.ClientError({'Error': {}}, 'message')
        mock_s3_client.return_value = Mock(head_object=Mock(side_effect=error))

        # expire time in the past in order to avoid sleeping
        self.assertRaises(pipeline.exceptions.VideoNotUploaded, aws_video.get_uploaded_video, 'key')


@utils.override_s3_settings
class TranscodeTests(TestCase):

    @override_settings(ELASTIC_TRANSCODER_PIPELINE_ID='pipelineid')
    @override_settings(ELASTIC_TRANSCODER_PRESETS={'SD': 'presetid'})
    @patch('contrib.plugins.aws.client.elastictranscoder_client')
    def test_transcode_video_success(self, mock_elastictranscoder_client):
        create_job_fixture = utils.load_json_fixture('elastictranscoder_create_job.json')
        read_job_fixture = utils.load_json_fixture('elastictranscoder_read_job_complete.json')
        mock_elastictranscoder_client.return_value = Mock(
            create_job=Mock(return_value=create_job_fixture),
            read_job=Mock(return_value=read_job_fixture)
        )

        progress = 0
        for progress in aws_video.transcode_video('videoid'):
            pass

        self.assertEqual(100, progress)
        mock_elastictranscoder_client.return_value.create_job.assert_called_once_with(
            PipelineId='pipelineid',
            Input={'Key': aws_utils.get_video_key('videoid', 'src')},
            Output={'PresetId': 'presetid', 'Key': aws_utils.get_video_key('videoid', 'SD')}
        )
        mock_elastictranscoder_client.return_value.read_job.assert_called_once_with(
            Id='jobid' # job id in test fixture
        )
