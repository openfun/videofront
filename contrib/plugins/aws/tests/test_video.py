from django.test import TestCase
from django.test.utils import override_settings

from mock import Mock, patch

from contrib.plugins.aws import backend as aws_backend
import pipeline.backend
import pipeline.exceptions
import pipeline.tasks
from . import utils


@utils.override_s3_settings
class VideoUploadUrlTests(TestCase):

    @patch('contrib.plugins.aws.backend.time')
    @patch('pipeline.utils.generate_video_id')
    def test_create_upload_url(self, mock_generate_video_id, mock_time):
        mock_time.return_value = 0
        backend = aws_backend.Backend()
        mock_generate_video_id.return_value = 'someid'
        backend._s3_client = Mock(
            generate_presigned_url=Mock(return_value="http://someurl")
        )

        upload_url = backend.create_upload_url('filename')

        self.assertEqual({
            'method': 'PUT',
            'url': "http://someurl",
            'expires_at': 3600,
            'id': 'someid'
        }, upload_url)

    @override_settings(PLUGIN_BACKEND='contrib.plugins.aws.backend.Backend')
    @patch('contrib.plugins.aws.backend.Backend.s3_client', Mock(
        generate_presigned_url=Mock(return_value="http://someurl")
    ))
    def test_create_upload_url_compatibility(self):
        upload_url = pipeline.tasks.create_upload_url('filename')
        self.assertEqual('http://someurl', upload_url['url'])

    def test_get_successfuly_uploaded_video(self):
        backend = aws_backend.Backend()
        backend._s3_client = Mock(list_objects=Mock(return_value={
            "Contents": [
                {'Key': 'videos/key/src/My file.mp4'}
            ]
        }))

        backend.get_uploaded_video('key')
        backend.s3_client.list_objects.assert_called_once_with(
            Bucket='dummys3storagebucket', Prefix='videos/key/src/'
        )

    def test_get_uploaded_video_for_not_uploaded_video(self):
        backend = aws_backend.Backend()
        backend._s3_client = Mock(list_objects=Mock(return_value={
            "Contents": []
        }))

        self.assertRaises(pipeline.exceptions.VideoNotUploaded, backend.get_uploaded_video, 'key')

    def test_delete_resources_no_content(self):
        backend = aws_backend.Backend()
        backend._s3_client = Mock(list_objects=Mock(return_value={}))
        backend.delete_resources('videoid')

        backend.s3_client.list_objects.assert_any_call(
            Bucket='dummys3storagebucket', Prefix='videos/videoid/'
        )


@utils.override_s3_settings
class TranscodeTests(TestCase):

    @override_settings(ELASTIC_TRANSCODER_PIPELINE_ID='pipelineid')
    @override_settings(ELASTIC_TRANSCODER_PRESETS=[('SD', 'presetid')])
    def test_transcode_video_success(self):
        create_job_fixture = utils.load_json_fixture('elastictranscoder_create_job.json')
        read_job_fixture = utils.load_json_fixture('elastictranscoder_read_job_complete.json')
        backend = aws_backend.Backend()

        backend.get_src_file_key = Mock(return_value='videos/videoid/src/Some video file.mpg')
        backend._elastictranscoder_client = Mock(
            create_job=Mock(return_value=create_job_fixture),
            read_job=Mock(return_value=read_job_fixture)
        )

        progress = 0
        for progress in backend.transcode_video('videoid'):
            pass

        self.assertEqual(100, progress)
        backend.elastictranscoder_client.create_job.assert_called_once_with(
            PipelineId='pipelineid',
            Input={'Key': 'videos/videoid/src/Some video file.mpg'},
            Output={'PresetId': 'presetid', 'Key': aws_backend.Backend.get_video_key('videoid', 'SD')}
        )
        backend.elastictranscoder_client.read_job.assert_called_once_with(
            Id='jobid' # job id in test fixture
        )
        backend.get_src_file_key.assert_called_once_with('videoid')
