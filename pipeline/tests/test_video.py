from time import time

from django.test import TestCase
from django.test.utils import override_settings

from pipeline import models
from pipeline.video import get_upload_url


class VideoUploadTests(TestCase):

    @override_settings(PLUGINS={"GET_UPLOAD_URL": lambda: {
        'url': 'http://example.com',
        'method': 'POST',
        'expires_at': time() + 60,
        'id': 'videoid'
    }})
    def test_get_upload_url(self):
        _upload_url = get_upload_url()
        should_check_urls = models.VideoUploadUrl.objects.should_check()

        self.assertEqual(1, should_check_urls.count())
        self.assertEqual('videoid', should_check_urls.get().public_video_id)
        self.assertEqual(False, should_check_urls.get().was_used)
        self.assertIsNone(should_check_urls.get().last_checked)
