from time import time

from django.test import TestCase

from mock import Mock, patch

from contrib.plugins.aws import tasks
from contrib.plugins.aws.videoupload import get_upload_url
from .utils import override_s3_settings


@override_s3_settings
class UploadUrlTests(TestCase):

    @patch('contrib.plugins.aws.videoupload.s3_client')
    @patch('contrib.plugins.aws.videoupload.generate_video_id')
    def test_url_provider(self, mock_generate_video_id, mock_s3_client):
        mock_s3_client.return_value = Mock(
            generate_presigned_url=Mock(return_value="http://someurl")
        )
        mock_generate_video_id.return_value = "someid"

        results = get_upload_url()

        self.assertEqual(3, len(results))
        self.assertEqual({
            'method': 'PUT',
            'url': "http://someurl"
        }, results[0])
        self.assertEqual("someid", results[1])

    @patch('contrib.plugins.aws.tasks.s3_client')
    def test_monitor_successful_upload(self, mock_s3_client):
        mock_s3_client.return_value = Mock(head_object=Mock(return_value=None))

        # Check no exception is raised
        # expire time in the future
        tasks.monitor_upload('key', time() + 10)
        # expire time in the past should start a transcode job anyway
        tasks.monitor_upload('key', time() - 10)

    @patch('contrib.plugins.aws.tasks.s3_client')
    def test_monitor_interrupted_upload(self, mock_s3_client):
        error = tasks.ClientError({'Error': {}}, 'message')
        mock_s3_client.return_value = Mock(head_object=Mock(side_effect=error))

        # expire time in the past in order to avoid sleeping
        self.assertRaises(tasks.VideoNotUploaded, tasks.monitor_upload, 'key', time() - 10)
