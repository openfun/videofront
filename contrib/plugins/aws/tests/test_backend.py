import shutil
from io import BytesIO

from django.test import TestCase
from django.test.utils import override_settings

from botocore.exceptions import ClientError
from mock import Mock, patch

import pipeline.backend
import pipeline.exceptions
import pipeline.tasks
from contrib.plugins.aws import backend as aws_backend
from pipeline.tests.factories import VideoFactory

from . import utils


@utils.override_s3_settings
class VideoUploadUrlTests(TestCase):
    def test_upload_video(self):
        backend = aws_backend.Backend()
        backend._s3_client = Mock(put_object=Mock())
        file_object = Mock()
        file_object.name = "somevideo.mp4"

        backend.upload_video("videoid", file_object)

        backend.s3_client.put_object.assert_called_once()
        self.assertEqual("private", backend.s3_client.put_object.call_args[1]["ACL"])
        self.assertEqual(
            "videos/videoid/src/somevideo.mp4",
            backend.s3_client.put_object.call_args[1]["Key"],
        )
        self.assertEqual(
            "privates3bucket", backend.s3_client.put_object.call_args[1]["Bucket"]
        )

    def test_delete_video_no_content(self):
        backend = aws_backend.Backend()
        backend._s3_client = Mock(list_objects=Mock(return_value={}))
        backend.delete_video("videoid")

        backend.s3_client.list_objects.assert_any_call(
            Bucket="privates3bucket", Prefix="videos/videoid/"
        )
        backend.s3_client.list_objects.assert_any_call(
            Bucket="publics3bucket", Prefix="videos/videoid/"
        )

    def test_delete_subtitle(self):
        backend = aws_backend.Backend()
        backend._s3_client = Mock(list_objects=Mock(return_value={}))
        backend.delete_subtitle("videoid", "subid")

        backend.s3_client.list_objects.assert_any_call(
            Bucket="publics3bucket", Prefix="videos/videoid/subs/subid."
        )

    @override_settings(PLUGIN_BACKEND="contrib.plugins.aws.backend.Backend")
    def test_video_url(self):
        backend = pipeline.backend.get()
        url = backend.video_url("videoid", "SD")
        self.assertIsNotNone(url)
        self.assertTrue(url.startswith("https://s3-dummyawsregion"))

    @override_settings(
        PLUGIN_BACKEND="contrib.plugins.aws.backend.Backend",
        CLOUDFRONT_DOMAIN_NAME="cloudfrontid.cloudfront.net",
    )
    def test_video_url_with_cloudfront(self):
        backend = pipeline.backend.get()
        url = backend.video_url("videoid", "SD")
        self.assertEqual(
            "https://cloudfrontid.cloudfront.net/videos/videoid/SD.mp4", url
        )


@utils.override_s3_settings
class TranscodeTests(TestCase):
    @override_settings(
        ELASTIC_TRANSCODER_PIPELINE_ID="pipelineid",
        ELASTIC_TRANSCODER_PRESETS=[("SD", "presetid", 128)],
        ELASTIC_TRANSCODER_THUMBNAILS_PRESET="thumbspresetid",
    )
    def test_start_transcoding(self):
        create_job_fixture = utils.load_json_fixture(
            "elastictranscoder_create_job.json"
        )
        backend = aws_backend.Backend()

        backend.get_src_file_key = Mock(
            return_value="videos/videoid/src/Some video file.mpg"
        )
        backend._elastictranscoder_client = Mock(
            create_job=Mock(return_value=create_job_fixture)
        )

        jobs = backend.start_transcoding("videoid")

        self.assertEqual(1, len(jobs))
        backend.elastictranscoder_client.create_job.assert_called_once_with(
            PipelineId="pipelineid",
            Input={"Key": "videos/videoid/src/Some video file.mpg"},
            Output={"PresetId": "presetid", "Key": "videos/videoid/SD.mp4"},
        )
        backend.get_src_file_key.assert_called_once_with("videoid")

    @override_settings(
        ELASTIC_TRANSCODER_PIPELINE_ID="pipelineid",
        ELASTIC_TRANSCODER_PRESETS=[
            ("SD", "sdpresetid", 128),
            ("HD", "hdpresetid", 256),
        ],
        ELASTIC_TRANSCODER_THUMBNAILS_PRESET="hdpresetid",
    )
    def test_start_transcoding_with_thumbnails(self):
        create_job_fixture = utils.load_json_fixture(
            "elastictranscoder_create_job.json"
        )
        backend = aws_backend.Backend()
        backend.get_src_file_key = Mock(
            return_value="videos/videoid/src/Some video file.mpg"
        )
        backend._elastictranscoder_client = Mock(
            create_job=Mock(return_value=create_job_fixture)
        )

        backend.start_transcoding("videoid")

        # SD + Thumbnails
        backend.elastictranscoder_client.create_job.assert_any_call(
            PipelineId="pipelineid",
            Input={"Key": "videos/videoid/src/Some video file.mpg"},
            Output={"PresetId": "sdpresetid", "Key": "videos/videoid/SD.mp4"},
        )

        # HD + Thumbnails
        backend.elastictranscoder_client.create_job.assert_any_call(
            PipelineId="pipelineid",
            Input={"Key": "videos/videoid/src/Some video file.mpg"},
            Output={
                "PresetId": "hdpresetid",
                "Key": "videos/videoid/HD.mp4",
                "ThumbnailPattern": "videos/videoid/thumbs/{count}",
            },
        )

    def test_check_progress(self):
        job = utils.load_json_fixture("elastictranscoder_create_job.json")
        read_job_fixture = utils.load_json_fixture(
            "elastictranscoder_read_job_complete.json"
        )
        backend = aws_backend.Backend()
        backend._elastictranscoder_client = Mock(
            read_job=Mock(return_value=read_job_fixture)
        )

        progress, finished = backend.check_progress(job["Job"])
        self.assertEqual(100, progress)
        self.assertTrue(finished)
        backend.elastictranscoder_client.read_job.assert_called_once_with(
            Id="jobid"  # job id in test fixture
        )

    @override_settings(
        ELASTIC_TRANSCODER_PIPELINE_ID="pipelineid",
        ELASTIC_TRANSCODER_PRESETS=[("SD", "presetid", 128)],
        ELASTIC_TRANSCODER_THUMBNAILS_PRESET="thumbspresetid",
    )
    def test_transcoding_pipeline_compatibility(self):
        create_job_fixture = utils.load_json_fixture(
            "elastictranscoder_create_job.json"
        )
        read_job_fixture = utils.load_json_fixture(
            "elastictranscoder_read_job_complete.json"
        )
        backend = aws_backend.Backend()
        backend.get_src_file_key = Mock(
            return_value="videos/videoid/src/Some video file.mpg"
        )
        backend._elastictranscoder_client = Mock(
            create_job=Mock(return_value=create_job_fixture),
            read_job=Mock(return_value=read_job_fixture),
        )

        jobs = backend.start_transcoding("videoid")
        backend.check_progress(jobs[0])

    @override_settings(
        ELASTIC_TRANSCODER_PRESETS=[("SD", "presetid1", 128), ("HD", "presetid2", 256)]
    )
    def test_iter_formats(self):
        backend = aws_backend.Backend()

        def head_object(Bucket=None, Key=None):
            if Key != "videos/videoid/HD.mp4":
                raise ClientError({"Error": {}}, "head_object")

        backend.s3_client.head_object = head_object
        formats = list(backend.iter_formats("videoid"))

        self.assertEqual([("HD", 256)], formats)


@utils.override_s3_settings
class ThumbnailsTests(TestCase):
    def setUp(self):
        VideoFactory(public_id="videoid")

    @patch("pipeline.utils.resize_image")
    @patch("contrib.plugins.aws.backend.Backend.s3_client")
    def test_create_thumbnail(self, mock_s3_client, mock_resize_image):
        thumbnail_file = BytesIO(b"")
        mock_s3_client.get_object = Mock(return_value={"Body": thumbnail_file})
        backend = aws_backend.Backend()

        backend.create_thumbnail("videoid", "thumbid")

        mock_s3_client.get_object.assert_called_once()
        self.assertEqual(
            "videos/videoid/thumbs/00001.png",
            mock_s3_client.get_object.call_args[1]["Key"],
        )
        mock_resize_image.assert_called_once()

    def test_thumbnail_url(self):
        backend = aws_backend.Backend()
        thumbnail_url = backend.thumbnail_url("videoid", "thumbid")
        self.assertIsNotNone(thumbnail_url)
        self.assertIn("videoid", thumbnail_url)
        self.assertIn("thumbid.jpg", thumbnail_url)

    @override_settings(PLUGIN_BACKEND="contrib.plugins.aws.backend.Backend")
    @patch("contrib.plugins.aws.backend.Backend.s3_client")
    def test_thumbnail_compatibility(self, mock_s3_client):
        def mock_resize_image(in_path, out_path, max_size):
            # Mock resize just copies the content from the source path to the
            # destination path
            self.assertIn(".jpg", out_path)
            shutil.copy(in_path, out_path)

        thumb_file = BytesIO(b"\x89PNG\r\n\x1a\n")
        thumb_file.name = "thumb.png"

        with patch("pipeline.utils.resize_image", mock_resize_image):
            pipeline.tasks.upload_thumbnail("videoid", thumb_file)

        mock_s3_client.put_object.assert_called_once()

    @override_settings(PLUGIN_BACKEND="contrib.plugins.aws.backend.Backend")
    @patch("contrib.plugins.aws.backend.Backend.s3_client")
    def test_delete_thumbnail(self, mock_s3_client):
        backend = aws_backend.Backend()

        backend.delete_thumbnail("videoid", "thumbid")

        mock_s3_client.delete_object.assert_called_once_with(
            Bucket="publics3bucket", Key="videos/videoid/thumbs/thumbid.jpg"
        )


@utils.override_s3_settings
class SubtitleTest(TestCase):
    @override_settings(PLUGIN_BACKEND="contrib.plugins.aws.backend.Backend")
    @patch("contrib.plugins.aws.backend.Backend.s3_client")
    def test_upload_subtitle_compatibility(self, mock_s3_client):
        pipeline.tasks.upload_subtitle("videoid", "subid", "fr", b"WEBVTT")
        mock_s3_client.put_object.assert_called_once()

    @override_settings(PLUGIN_BACKEND="contrib.plugins.aws.backend.Backend")
    def test_subtitle_url_compatibility(self):
        video = VideoFactory(public_id="videoid")
        subtitle = video.subtitles.create(language="fr")
        self.assertIsNotNone(subtitle.url)

    def subtitle_url(self):
        backend = aws_backend.Backend()
        url = backend.subtitle_url("videoid", "subid", "uk")
        self.assertIsNotNone(url)
        self.assertIn("videoid", url)
        self.assertIn("subid", url)
        self.assertIn("uk", url)

    @override_settings(CLOUDFRONT_DOMAIN_NAME="cloudfrontid.cloudfront.net")
    def test_subtitle_url(self):
        backend = aws_backend.Backend()
        url = backend.subtitle_url("videoid", "subid", "uk")
        self.assertTrue(url.startswith("https://cloudfrontid.cloudfront.net"))
