from botocore.exceptions import ClientError
from django.test import TestCase
from django.test.utils import override_settings

from mock import Mock, patch

from contrib.plugins.aws import backend as aws_backend
import pipeline.backend
import pipeline.exceptions
import pipeline.tasks
from pipeline.tests.factories import UserFactory, VideoFactory
from . import utils


@utils.override_s3_settings
class VideoUploadUrlTests(TestCase):

    @patch('contrib.plugins.aws.backend.time')
    @patch('pipeline.utils.generate_random_id')
    def test_get_upload_url(self, mock_generate_random_id, mock_time):
        mock_time.return_value = 0
        backend = aws_backend.Backend()
        mock_generate_random_id.return_value = 'someid'
        backend._s3_client = Mock(
            generate_presigned_url=Mock(return_value="http://someurl")
        )

        upload_url = backend.get_upload_url('filename')

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
    def test_get_upload_url_compatibility(self):
        user = UserFactory()
        upload_url = pipeline.tasks.get_upload_url(user.id, 'filename')
        self.assertEqual('http://someurl', upload_url['url'])

    def test_get_successfuly_uploaded_video(self):
        backend = aws_backend.Backend()
        backend._s3_client = Mock(list_objects=Mock(return_value={
            "Contents": [
                {'Key': 'videos/key/src/My file.mp4'}
            ]
        }))

        backend.check_video('key')
        backend.s3_client.list_objects.assert_called_once_with(
            Bucket='dummys3storagebucket', Prefix='videos/key/src/'
        )

    def test_get_uploaded_video_for_not_uploaded_video(self):
        backend = aws_backend.Backend()
        backend._s3_client = Mock(list_objects=Mock(return_value={
            "Contents": []
        }))

        self.assertRaises(pipeline.exceptions.VideoNotUploaded, backend.check_video, 'key')

    def test_delete_video_no_content(self):
        backend = aws_backend.Backend()
        backend._s3_client = Mock(list_objects=Mock(return_value={}))
        backend.delete_video('videoid')

        backend.s3_client.list_objects.assert_any_call(
            Bucket='dummys3storagebucket', Prefix='videos/videoid/'
        )

    def test_delete_subtitle(self):
        backend = aws_backend.Backend()
        backend._s3_client = Mock(list_objects=Mock(return_value={}))
        backend.delete_subtitle('videoid', 'subid')

        backend.s3_client.list_objects.assert_any_call(
            Bucket='dummys3storagebucket', Prefix='videos/videoid/subs/subid.'
        )

    @override_settings(PLUGIN_BACKEND='contrib.plugins.aws.backend.Backend')
    def test_video_url(self):
        backend = pipeline.backend.get()
        url = backend.video_url('videoid', 'SD')
        self.assertIsNotNone(url)
        self.assertTrue(url.startswith("https://s3-dummyawsregion"))

    @override_settings(
        PLUGIN_BACKEND='contrib.plugins.aws.backend.Backend',
        CLOUDFRONT_DOMAIN_NAME='cloudfrontid.cloudfront.net'
    )
    def test_video_url_with_cloudfront(self):
        backend = pipeline.backend.get()
        url = backend.video_url('videoid', 'SD')
        self.assertEqual("https://cloudfrontid.cloudfront.net/videos/videoid/SD.mp4", url)


@utils.override_s3_settings
class TranscodeTests(TestCase):

    @override_settings(ELASTIC_TRANSCODER_PIPELINE_ID='pipelineid')
    @override_settings(ELASTIC_TRANSCODER_PRESETS=[('SD', 'presetid', 128)])
    def test_start_transcoding(self):
        create_job_fixture = utils.load_json_fixture('elastictranscoder_create_job.json')
        backend = aws_backend.Backend()

        backend.get_src_file_key = Mock(return_value='videos/videoid/src/Some video file.mpg')
        backend._elastictranscoder_client = Mock(
            create_job=Mock(return_value=create_job_fixture),
        )

        jobs = backend.start_transcoding('videoid')

        self.assertEqual(1, len(jobs))
        backend.elastictranscoder_client.create_job.assert_called_once_with(
            PipelineId='pipelineid',
            Input={'Key': 'videos/videoid/src/Some video file.mpg'},
            Output={'PresetId': 'presetid', 'Key': aws_backend.Backend.get_video_key('videoid', 'SD')}
        )
        backend.get_src_file_key.assert_called_once_with('videoid')

    def test_check_progress(self):
        job = utils.load_json_fixture('elastictranscoder_create_job.json')
        read_job_fixture = utils.load_json_fixture('elastictranscoder_read_job_complete.json')
        backend = aws_backend.Backend()
        backend._elastictranscoder_client = Mock(
            read_job=Mock(return_value=read_job_fixture),
        )

        progress, finished = backend.check_progress(job['Job'])
        self.assertEqual(100, progress)
        self.assertTrue(finished)
        backend.elastictranscoder_client.read_job.assert_called_once_with(
            Id='jobid' # job id in test fixture
        )

    @override_settings(ELASTIC_TRANSCODER_PIPELINE_ID='pipelineid')
    @override_settings(ELASTIC_TRANSCODER_PRESETS=[('SD', 'presetid', 128)])
    def test_transcoding_pipeline_compatibility(self):
        create_job_fixture = utils.load_json_fixture('elastictranscoder_create_job.json')
        read_job_fixture = utils.load_json_fixture('elastictranscoder_read_job_complete.json')
        backend = aws_backend.Backend()
        backend.get_src_file_key = Mock(return_value='videos/videoid/src/Some video file.mpg')
        backend._elastictranscoder_client = Mock(
            create_job=Mock(return_value=create_job_fixture),
            read_job=Mock(return_value=read_job_fixture)
        )

        jobs = backend.start_transcoding('videoid')
        backend.check_progress(jobs[0])

    @override_settings(ELASTIC_TRANSCODER_PRESETS=[('SD', 'presetid1', 128), ('HD', 'presetid2', 256)])
    def test_iter_formats(self):
        backend = aws_backend.Backend()

        def head_object(Bucket=None, Key=None):
            if Key != 'videos/videoid/HD.mp4':
                raise ClientError({'Error': {}}, 'head_object')

        backend.s3_client.head_object = head_object
        formats = list(backend.iter_formats('videoid'))

        self.assertEqual([('HD', 256)], formats)

@utils.override_s3_settings
class SubtitleTest(TestCase):

    @override_settings(PLUGIN_BACKEND='contrib.plugins.aws.backend.Backend')
    @patch('contrib.plugins.aws.backend.Backend.s3_client')
    def test_upload_subtitle_compatibility(self, mock_s3_client):
        pipeline.tasks.upload_subtitle('videoid', 'subid', 'fr', b"WEBVTT")
        mock_s3_client.put_object.assert_called_once()

    @override_settings(PLUGIN_BACKEND='contrib.plugins.aws.backend.Backend')
    def test_subtitle_url_compatibility(self):
        video = VideoFactory(public_id='videoid')
        subtitle = video.subtitles.create(language='fr')
        self.assertIsNotNone(subtitle.url)

    def subtitle_url(self):
        backend = aws_backend.Backend()
        url = backend.subtitle_url('videoid', 'subid', 'uk')
        self.assertIsNotNone(url)
        self.assertIn('videoid', url)
        self.assertIn('subid', url)
        self.assertIn('uk', url)

    @override_settings(CLOUDFRONT_DOMAIN_NAME='cloudfrontid.cloudfront.net')
    def test_subtitle_url(self):
        backend = aws_backend.Backend()
        url = backend.subtitle_url('videoid', 'subid', 'uk')
        self.assertTrue(url.startswith('https://cloudfrontid.cloudfront.net'))
