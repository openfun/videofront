from time import time

from django.test import TestCase
from django.test.utils import override_settings

from pipeline import models
from pipeline.video import get_upload_url


class VideoUploadTests(TestCase):

    @override_settings(PLUGINS={"GET_UPLOAD_URL": lambda filename: {
        'url': 'http://example.com',
        'method': 'POST',
        'expires_at': time() + 60,
        'id': 'videoid'
    }})
    def test_get_upload_url(self):
        _upload_url = get_upload_url('video.mp4')
        should_check_urls = models.VideoUploadUrl.objects.should_check()

        self.assertEqual(1, should_check_urls.count())
        url = should_check_urls.get()
        self.assertEqual('videoid', url.public_video_id)
        self.assertEqual(False, url.was_used)
        self.assertIsNone(url.last_checked)
        self.assertEqual('video.mp4', url.filename)
