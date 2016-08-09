from time import time
import mock

from django.test import TestCase

from pipeline import exceptions
from pipeline import models
from pipeline import tasks
from pipeline.tests.utils import override_plugins


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
        transcode_video = mock.Mock(return_value=[100])

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

        with override_plugins(
                GET_UPLOADED_VIDEO=get_uploaded_video,
                TRANSCODE_VIDEO=transcode_video
        ):
            tasks.monitor_uploads()

        url1 = models.VideoUploadUrl.objects.get(public_video_id='videoid1')
        url2 = models.VideoUploadUrl.objects.get(public_video_id='videoid2')

        self.assertFalse(url1.was_used)
        self.assertTrue(url2.was_used)
        self.assertIsNotNone(url1.last_checked)
        self.assertIsNotNone(url2.last_checked)
        self.assertEqual(1, models.Video.objects.count())
        self.assertEqual('video2.mp4', models.Video.objects.get().title)
        transcode_video.assert_called_once_with('videoid2')

    def test_monitor_uploads_task(self):
        tasks.monitor_uploads_task()

        # Check lock is available
        tasks.acquire_lock('MONITOR_UPLOADS_TASK_LOCK')


    def test_monitor_uploads_with_one_expired_url(self):
        models.VideoUploadUrl.objects.create(public_video_id='videoid', expires_at=time() - 7200,
                                             was_used=False, last_checked=None)
        transcode_video = mock.Mock(return_value=[100])

        with override_plugins(
                GET_UPLOADED_VIDEO=lambda public_video_id: None,
                TRANSCODE_VIDEO=transcode_video
        ):
            tasks.monitor_uploads()

        # We want upload urls to be checked at least once even after they expired.
        self.assertTrue(models.VideoUploadUrl.objects.get(public_video_id='videoid').was_used)
        transcode_video.assert_called_once_with('videoid')

    def test_transcode_video_success(self):
        transcode_video = mock.Mock(return_value=[100])

        with override_plugins(TRANSCODE_VIDEO=transcode_video):
            tasks.transcode_video('videoid')

        self.assertEqual(1, models.VideoTranscoding.objects.count())
        video_transcoding = models.VideoTranscoding.objects.get()
        self.assertEqual(models.VideoTranscoding.STATUS_SUCCESS, video_transcoding.status)
        self.assertEqual(100, video_transcoding.progress)
