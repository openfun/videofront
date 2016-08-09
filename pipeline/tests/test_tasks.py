from datetime import timedelta
from time import time
from mock import Mock

from django.test import TestCase
from django.test.utils import override_settings
from django.utils.timezone import now

from pipeline import exceptions
from pipeline import models
from pipeline import tasks


class TasksTests(TestCase):

    def test_acquire_lock(self):
        self.assertTrue(tasks.acquire_lock("dummylock"))
        self.assertRaises(exceptions.LockUnavailable, tasks.acquire_lock, "dummylock")
        tasks.release_lock('dummylock')
        self.assertTrue(tasks.acquire_lock("dummylock"))

    def test_monitor_uploads(self):
        def get_uploaded_video(video_id):
            if video_id == "videoid1":
                raise exceptions.VideoNotUploaded

        models.VideoUploadUrl.objects.create(
            public_video_id='videoid1',
            filename="video1.mp4",
            expires_at=time() + 3600
        )
        models.VideoUploadUrl.objects.create(
            public_video_id='videoid2',
            filename="video2.mp4",
            expires_at=time() + 3600
        )
        mock_backend = Mock(return_value=Mock(
            transcode_video=Mock(return_value=[100]),
            get_uploaded_video=get_uploaded_video
        ))

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
        mock_backend.return_value.transcode_video.assert_called_once_with('videoid2')

    def test_monitor_uploads_task(self):
        tasks.monitor_uploads_task()

        # Check lock is available
        tasks.acquire_lock('MONITOR_UPLOADS_TASK_LOCK')


    def test_monitor_uploads_with_one_expired_url(self):
        models.VideoUploadUrl.objects.create(public_video_id='videoid', expires_at=time() - 7200,
                                             was_used=False, last_checked=None)
        mock_backend = Mock(return_value=Mock(transcode_video=Mock(return_value=[100])))
        with override_settings(PLUGIN_BACKEND=mock_backend):
            tasks.monitor_uploads()

        # We want upload urls to be checked at least once even after they expired.
        self.assertTrue(models.VideoUploadUrl.objects.get(public_video_id='videoid').was_used)
        mock_backend.return_value.transcode_video.assert_called_once_with('videoid')

    def test_monitor_uploads_for_already_created_video(self):
        models.VideoUploadUrl.objects.create(public_video_id='videoid',
                                             expires_at=time() + 3600,
                                             was_used=False,
                                             last_checked=None)
        models.Video.objects.create(public_id='videoid')

        # Simulate a monitoring task that runs while the video has alreay been created
        mock_backend = Mock(return_value=Mock(
            transcode_video=Mock(return_value=[100])
        ))
        with override_settings(PLUGIN_BACKEND=mock_backend):
            tasks.monitor_uploads()

        mock_backend.return_value.transcode_video.assert_not_called()

    def test_monitor_upload_of_url_with_last_checked_in_future(self):
        last_checked = now() + timedelta(seconds=100)
        models.VideoUploadUrl.objects.create(public_video_id='videoid',
                                             expires_at=time() + 3600,
                                             was_used=False,
                                             last_checked=last_checked)

        mock_backend = Mock(return_value=Mock(
            get_uploaded_video=Mock(side_effect=exceptions.VideoNotUploaded)
        ))
        with override_settings(PLUGIN_BACKEND=mock_backend):
            tasks.monitor_uploads()

        self.assertEqual(last_checked, models.VideoUploadUrl.objects.get().last_checked)

    def test_transcode_video_success(self):
        mock_backend = Mock(return_value=Mock(
            transcode_video=Mock(return_value=[100])
        ))

        with override_settings(PLUGIN_BACKEND=mock_backend):
            tasks.transcode_video('videoid')

        self.assertEqual(1, models.VideoTranscoding.objects.count())
        video_transcoding = models.VideoTranscoding.objects.get()
        self.assertEqual(models.VideoTranscoding.STATUS_SUCCESS, video_transcoding.status)
        self.assertEqual(100, video_transcoding.progress)
