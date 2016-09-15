import os
from time import time
from mock import Mock

from django.db.utils import IntegrityError
from django.test import TestCase, TransactionTestCase
from django.test.utils import override_settings

from pipeline import exceptions
from pipeline import models
from pipeline import tasks
from pipeline.tests import factories
from videofront.celery_videofront import send_task


class LockTests(TransactionTestCase):
    """
    Tests in this test case will not be wrapped inside an atomic transaction. Do not create data in this test case.
    """

    def setUp(self):
        tasks.release_lock('dummylock')

    def tearDown(self):
        tasks.release_lock('dummylock')

    def test_acquire_release_lock_cycle(self):
        self.assertTrue(tasks.acquire_lock("dummylock"))
        self.assertRaises(exceptions.LockUnavailable, tasks.acquire_lock, "dummylock")
        tasks.release_lock('dummylock')
        self.assertTrue(tasks.acquire_lock("dummylock"))

    def test_release_lock_with_integrity_error(self):
        def failing_task():
            tasks.acquire_lock('dummylock', 3600)

            try:
                models.Video.objects.create(public_id="id")
                models.Video.objects.create(public_id="id")
            finally:
                tasks.release_lock('dummylock')

        self.assertRaises(IntegrityError, failing_task)
        self.assertTrue(tasks.acquire_lock("dummylock"))

    def test_context_manager(self):

        # 1) Lock is available
        with tasks.Lock('dummylock') as lock:
            self.assertTrue(lock.is_acquired)
            self.assertRaises(exceptions.LockUnavailable, tasks.acquire_lock, "dummylock")

        self.assertFalse(lock.is_acquired)

        # 2) Lock is unavailable
        tasks.acquire_lock("dummylock")
        with tasks.Lock('dummylock') as lock:
            self.assertFalse(lock.is_acquired)

        self.assertRaises(exceptions.LockUnavailable, tasks.acquire_lock, "dummylock")


class TasksTests(TestCase):

    def test_upload_video(self):
        mock_backend = Mock(return_value=Mock(
            upload_video=Mock(),
            start_transcoding=Mock(return_value=[]),
            iter_formats=Mock(return_value=[]),
        ))
        factories.VideoUploadUrlFactory(
            was_used=False,
            public_video_id='videoid',
            expires_at=time() + 3600
        )
        file_object = Mock()
        file_object.name = "Some video.mp4"
        with override_settings(PLUGIN_BACKEND=mock_backend):
            tasks.upload_video('videoid', file_object)

        self.assertEqual(1, models.Video.objects.count())
        self.assertEqual(1, models.VideoUploadUrl.objects.count())
        video = models.Video.objects.get()
        video_upload_url = models.VideoUploadUrl.objects.get()
        self.assertEqual("Some video.mp4", video.title)
        self.assertLess(10, len(video.public_thumbnail_id))
        self.assertTrue(video_upload_url.was_used)

    def test_transcode_video_success(self):
        factories.VideoFactory(public_id='videoid', public_thumbnail_id='thumbid')
        mock_backend = Mock(return_value=Mock(
            start_transcoding=Mock(return_value=['job1']),
            check_progress=Mock(return_value=(42, True)),
            iter_formats=Mock(return_value=[('SD', 128)]),
            create_thumbnail=Mock(),
        ))

        with override_settings(PLUGIN_BACKEND=mock_backend):
            tasks.transcode_video('videoid')

        self.assertEqual(1, models.ProcessingState.objects.count())
        video_processing_state = models.ProcessingState.objects.get()
        self.assertEqual(models.ProcessingState.STATUS_SUCCESS, video_processing_state.status)
        self.assertEqual("", video_processing_state.message)
        self.assertEqual(42, video_processing_state.progress)
        mock_backend.return_value.create_thumbnail.assert_called_once_with('videoid', 'thumbid')
        mock_backend.return_value.check_progress.assert_called_once_with('job1')
        self.assertEqual(1, models.VideoFormat.objects.count())
        video_format = models.VideoFormat.objects.get()
        self.assertEqual('videoid', video_format.video.public_id)
        self.assertEqual('SD', video_format.name)
        self.assertEqual(128, video_format.bitrate)

    def test_transcode_video_failure(self):
        factories.VideoFactory(public_id='videoid')

        def check_progress(job):
            if job == 'job1':
                # job1 finishes
                raise exceptions.TranscodingFailed('error message')
            else:
                # job2 finishes
                return 100, True

        mock_backend = Mock(return_value=Mock(
            start_transcoding=Mock(return_value=['job1', 'job2']),
            check_progress=check_progress,
            iter_formats=Mock(return_value=[]),
        ))

        with override_settings(PLUGIN_BACKEND=mock_backend):
            tasks.transcode_video('videoid')

        self.assertEqual(1, models.ProcessingState.objects.count())
        video_processing_state = models.ProcessingState.objects.get()
        self.assertEqual(models.ProcessingState.STATUS_FAILED, video_processing_state.status)
        self.assertEqual("error message", video_processing_state.message)
        self.assertEqual(50, video_processing_state.progress)

    def test_transcode_video_unexpected_failure(self):
        factories.VideoFactory(public_id='videoid')

        mock_backend = Mock(return_value=Mock(
            start_transcoding=Mock(side_effect=ValueError("random error"))
        ))

        with override_settings(PLUGIN_BACKEND=mock_backend):
            self.assertRaises(ValueError, tasks.transcode_video, 'videoid')

        video_processing_state = models.ProcessingState.objects.get()
        self.assertEqual(models.ProcessingState.STATUS_FAILED, video_processing_state.status)
        self.assertEqual("random error", video_processing_state.message)

    def test_transcode_video_twice(self):
        factories.VideoFactory(public_id='videoid')
        mock_backend = Mock(return_value=Mock(
            start_transcoding=Mock(return_value=['job1']),
            iter_formats=Mock(return_value=[]),
        ))

        # First attempt: failure
        mock_backend.return_value.check_progress = Mock(side_effect=exceptions.TranscodingFailed)
        with override_settings(PLUGIN_BACKEND=mock_backend):
            tasks.transcode_video('videoid')

        # Second attempt: success
        mock_backend.return_value.check_progress = Mock(return_value=(100, True))
        with override_settings(PLUGIN_BACKEND=mock_backend):
            tasks.transcode_video('videoid')

        video_processing_state = models.ProcessingState.objects.get()
        self.assertEqual(models.ProcessingState.STATUS_SUCCESS, video_processing_state.status)
        self.assertEqual("", video_processing_state.message)
        self.assertEqual(100, video_processing_state.progress)

    def test_transcode_video_restart(self):
        video = factories.VideoFactory(public_id='videoid')
        models.ProcessingState.objects.filter(video=video).update(status=models.ProcessingState.STATUS_RESTART)

        mock_backend = Mock(return_value=Mock(
            start_transcoding=Mock(return_value=[]),
            iter_formats=Mock(return_value=[]),
        ))
        with override_settings(PLUGIN_BACKEND=mock_backend):
            tasks.transcode_video_restart()

        mock_backend.return_value.start_transcoding.assert_called_once_with('videoid')
        self.assertEqual(
            models.ProcessingState.STATUS_SUCCESS,
            models.ProcessingState.objects.get(video=video).status
        )

    def test_transcode_video_restart_fails(self):
        video = factories.VideoFactory(public_id='videoid')
        models.ProcessingState.objects.filter(video=video).update(status=models.ProcessingState.STATUS_RESTART)

        mock_backend = Mock(return_value=Mock(
            start_transcoding=Mock(return_value=[1]),
            check_progress=Mock(side_effect=exceptions.TranscodingFailed),
        ))
        with override_settings(PLUGIN_BACKEND=mock_backend):
            tasks.transcode_video_restart()

        self.assertEqual(
            models.ProcessingState.STATUS_FAILED,
            models.ProcessingState.objects.get(video=video).status
        )
        mock_backend.return_value.delete_video.assert_not_called()


class SubtitleTasksTest(TestCase):

    def test_upload_subtitle(self):
        srt_content = """1
00:00:00,822 --> 00:00:01,565
Hello world!

2
00:00:01,840 --> 00:00:03,280
My name is VIDEOFRONT and I am awesome.

3
00:00:03,920 --> 00:00:08,250
Also I have utf8 characters: é û ë ï 你好."""
        vtt_content = """WEBVTT

00:00.822 --> 00:01.565
Hello world!

00:01.840 --> 00:03.280
My name is VIDEOFRONT and I am awesome.

00:03.920 --> 00:08.250
Also I have utf8 characters: é û ë ï 你好.
"""

        mock_backend = Mock(return_value=Mock(upload_subtitle=Mock()))
        with override_settings(PLUGIN_BACKEND=mock_backend):
            tasks.upload_subtitle('videoid', 'subtitleid', 'fr', srt_content.encode('utf-8'))
        mock_backend.return_value.upload_subtitle.assert_called_once_with('videoid', 'subtitleid', 'fr', vtt_content)

    def test_upload_subtitle_with_invalid_format(self):
        mock_backend = Mock(return_value=Mock(upload_subtitle=Mock()))
        with override_settings(PLUGIN_BACKEND=mock_backend):
            self.assertRaises(
                exceptions.SubtitleInvalid,
                tasks.upload_subtitle, 'videoid', 'subtitleid', 'fr', b'Some invalid content'
            )

class UploadUrlsTasksTests(TestCase):

    def test_clean_upload_urls(self):
        factories.VideoUploadUrlFactory(
            public_video_id='available',
            expires_at=time(),
            was_used=False
        )
        factories.VideoUploadUrlFactory(
            public_video_id='expired',
            expires_at=time() - 7200,
            was_used=False
        )
        factories.VideoUploadUrlFactory(
            public_video_id='expired_used',
            expires_at=time() - 7200,
            was_used=True
        )
        send_task('clean_upload_urls')

        upload_url_ids = [url.public_video_id for url in models.VideoUploadUrl.objects.all()]

        self.assertIn('available', upload_url_ids)
        self.assertIn('expired_used', upload_url_ids)
        self.assertEqual(2, len(upload_url_ids))


class UploadThumbnailTests(TestCase):

    def test_upload_thumbnail(self):
        factories.VideoFactory(public_id="videoid", public_thumbnail_id="old_thumbid")
        img = open(os.path.join(os.path.dirname(__file__), 'fixtures', 'elcapitan.jpg'), 'rb')

        mock_backend = Mock(return_value=Mock(
            upload_thumbnail=Mock(),
            delete_thumbnail=Mock(),
        ))
        with override_settings(PLUGIN_BACKEND=mock_backend):
            tasks.upload_thumbnail("videoid", img)

        mock_backend.return_value.upload_thumbnail.assert_called_once()
        mock_backend.return_value.delete_thumbnail.assert_called_once_with("videoid", "old_thumbid")
