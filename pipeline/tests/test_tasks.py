from datetime import timedelta
from time import time
from mock import Mock

from django.db.utils import IntegrityError
from django.test import TestCase, TransactionTestCase
from django.test.utils import override_settings
from django.utils.timezone import now

from pipeline import exceptions
from pipeline import models
from pipeline import tasks
from pipeline.tests import factories


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


class TasksTests(TestCase):

    def test_monitor_uploads(self):
        def get_uploaded_video(video_id):
            if video_id == "videoid1":
                raise exceptions.VideoNotUploaded
        mock_backend = Mock(return_value=Mock(
            create_transcoding_jobs=Mock(return_value=[]),# Don't start any transcoding
            get_uploaded_video=get_uploaded_video,
            iter_available_formats=Mock(return_value=[]),
        ))

        factories.VideoUploadUrlFactory(
            public_video_id='videoid1',
            filename="video1.mp4",
            expires_at=time() + 3600
        )
        factories.VideoUploadUrlFactory(
            public_video_id='videoid2',
            filename="video2.mp4",
            expires_at=time() + 3600
        )

        with override_settings(PLUGIN_BACKEND=mock_backend):
            tasks.monitor_uploads()

        url1 = models.VideoUploadUrl.objects.get(public_video_id='videoid1')
        url2 = models.VideoUploadUrl.objects.get(public_video_id='videoid2')

        self.assertFalse(url1.was_used)
        self.assertTrue(url2.was_used)
        self.assertIsNotNone(url1.last_checked)
        self.assertIsNotNone(url2.last_checked)
        self.assertEqual(1, models.Video.objects.count())
        self.assertEqual('video2.mp4', models.Video.objects.get().title)
        self.assertEqual(url2.owner, models.Video.objects.get().owner)
        mock_backend.return_value.create_transcoding_jobs.assert_called_once_with('videoid2')

    def test_monitor_uploads_task(self):
        tasks.monitor_uploads_task()

        # Check lock is available
        tasks.acquire_lock('MONITOR_UPLOADS_TASK_LOCK')


    def test_monitor_uploads_with_one_expired_url(self):
        factories.VideoUploadUrlFactory(
            public_video_id='videoid', expires_at=time() - 7200,
            was_used=False, last_checked=None
        )
        mock_backend = Mock(return_value=Mock(
            create_transcoding_jobs=Mock(return_value=[]),
            iter_available_formats=Mock(return_value=[]),
        ))
        with override_settings(PLUGIN_BACKEND=mock_backend):
            tasks.monitor_uploads()

        # We want upload urls to be checked at least once even after they expired.
        self.assertTrue(models.VideoUploadUrl.objects.get(public_video_id='videoid').was_used)
        mock_backend.return_value.create_transcoding_jobs.assert_called_once_with('videoid')

    def test_monitor_uploads_for_already_created_video(self):
        upload_url = factories.VideoUploadUrlFactory(
            public_video_id='videoid',
            expires_at=time() + 3600,
            was_used=False,
            last_checked=None
        )
        factories.VideoFactory(public_id='videoid', owner=upload_url.owner)

        # Simulate a monitoring task that runs while the video has alreay been created
        mock_backend = Mock(return_value=Mock(
            transcode_video=Mock(return_value=[100])
        ))
        with override_settings(PLUGIN_BACKEND=mock_backend):
            tasks.monitor_uploads()

        mock_backend.return_value.transcode_video.assert_not_called()

    def test_monitor_upload_of_url_with_last_checked_in_future(self):
        last_checked = now() + timedelta(seconds=100)
        factories.VideoUploadUrlFactory(
            public_video_id='videoid',
            expires_at=time() + 3600,
            was_used=False,
            last_checked=last_checked,
        )

        mock_backend = Mock(return_value=Mock(
            get_uploaded_video=Mock(side_effect=exceptions.VideoNotUploaded)
        ))
        with override_settings(PLUGIN_BACKEND=mock_backend):
            tasks.monitor_uploads()

        self.assertEqual(last_checked, models.VideoUploadUrl.objects.get().last_checked)

    def test_monitor_upload_of_url_with_playlist(self):
        playlist = factories.PlaylistFactory()
        factories.VideoUploadUrlFactory(
            public_video_id='videoid',
            expires_at=time() + 3600,
            was_used=False,
            playlist=playlist
        )

        mock_backend = Mock(return_value=Mock(
            create_transcoding_jobs=Mock(return_value=[]),
            iter_available_formats=Mock(return_value=[]),
        ))
        with override_settings(PLUGIN_BACKEND=mock_backend):
            tasks.monitor_uploads()

        video = models.Video.objects.get()
        self.assertEqual(1, video.playlists.count())
        self.assertEqual(playlist.id, video.playlists.get().id)

    def test_transcode_video_success(self):
        factories.VideoFactory(public_id='videoid')
        mock_backend = Mock(return_value=Mock(
            create_transcoding_jobs=Mock(return_value=['job1']),
            get_transcoding_job_progress=Mock(return_value=(42, True)),
            iter_available_formats=Mock(return_value=[('SD', 128)]),
        ))

        with override_settings(PLUGIN_BACKEND=mock_backend):
            tasks.transcode_video('videoid')

        self.assertEqual(1, models.VideoTranscoding.objects.count())
        video_transcoding = models.VideoTranscoding.objects.get()
        self.assertEqual(models.VideoTranscoding.STATUS_SUCCESS, video_transcoding.status)
        self.assertEqual("", video_transcoding.message)
        self.assertEqual(42, video_transcoding.progress)
        mock_backend.return_value.get_transcoding_job_progress.assert_called_once_with('job1')
        self.assertEqual(1, models.VideoFormat.objects.count())
        video_format = models.VideoFormat.objects.get()
        self.assertEqual('videoid', video_format.video.public_id)
        self.assertEqual('SD', video_format.name)
        self.assertEqual(128, video_format.bitrate)

    def test_transcode_video_failure(self):
        factories.VideoFactory(public_id='videoid')

        def get_transcoding_job_progress(job):
            if job == 'job1':
                # job1 finishes
                raise exceptions.TranscodingFailed('error message')
            else:
                # job2 finishes
                return 100, True

        mock_backend = Mock(return_value=Mock(
            create_transcoding_jobs=Mock(return_value=['job1', 'job2']),
            get_transcoding_job_progress=get_transcoding_job_progress,
            iter_available_formats=Mock(return_value=[]),
        ))

        with override_settings(PLUGIN_BACKEND=mock_backend):
            tasks.transcode_video('videoid')

        self.assertEqual(1, models.VideoTranscoding.objects.count())
        video_transcoding = models.VideoTranscoding.objects.get()
        self.assertEqual(models.VideoTranscoding.STATUS_FAILED, video_transcoding.status)
        self.assertEqual("error message", video_transcoding.message)
        self.assertEqual(50, video_transcoding.progress)

    def test_transcode_video_twice(self):
        factories.VideoFactory(public_id='videoid')
        mock_backend = Mock(return_value=Mock(
            create_transcoding_jobs=Mock(return_value=['job1']),
            iter_available_formats=Mock(return_value=[]),
        ))

        # First attempt: failure
        mock_backend.return_value.get_transcoding_job_progress = Mock(side_effect=exceptions.TranscodingFailed)
        with override_settings(PLUGIN_BACKEND=mock_backend):
            tasks.transcode_video('videoid')

        # Second attempt: success
        mock_backend.return_value.get_transcoding_job_progress = Mock(return_value=(100, True))
        with override_settings(PLUGIN_BACKEND=mock_backend):
            tasks.transcode_video('videoid')

        video_transcoding = models.VideoTranscoding.objects.get()
        self.assertEqual(models.VideoTranscoding.STATUS_SUCCESS, video_transcoding.status)
        self.assertEqual("", video_transcoding.message)
        self.assertEqual(100, video_transcoding.progress)


class SubtitlesTasksTest(TestCase):

    def test_upload_subtitles(self):
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

        mock_backend = Mock(return_value=Mock(upload_subtitles=Mock()))
        with override_settings(PLUGIN_BACKEND=mock_backend):
            tasks.upload_subtitles('videoid', 'subtitlesid', 'fr', srt_content.encode('utf-8'))
        mock_backend.return_value.upload_subtitles.assert_called_once_with('videoid', 'subtitlesid', 'fr', vtt_content)

    def test_upload_subtitles_with_invalid_format(self):
        mock_backend = Mock(return_value=Mock(upload_subtitles=Mock()))
        with override_settings(PLUGIN_BACKEND=mock_backend):
            self.assertRaises(
                exceptions.SubtitlesInvalid,
                tasks.upload_subtitles, 'videoid', 'subtitlesid', 'fr', b'Some invalid content'
            )
