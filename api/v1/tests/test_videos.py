import json

from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.test.utils import override_settings

from video.models import Video


class ApiV1VideosUnauthenticatedTests(TestCase):

    def test_list_videos(self):
        url = reverse("api:v1:video-list")
        response = self.client.get(url)
        # BasicAuthentication returns a 401 in case
        self.assertEqual(401, response.status_code)


class ApiV1VideosTests(TestCase):

    def setUp(self):
        user = User.objects.create(username="test", is_active=True)
        user.set_password("password")
        user.save()
        self.client.login(username="test", password="password")

    def test_list_videos(self):
        url = reverse("api:v1:video-list")
        response = self.client.get(url)
        videos = json.loads(response.content)

        self.assertEqual(200, response.status_code)
        self.assertEqual([], videos)

    def test_create_video(self):
        url = reverse("api:v1:video-list")
        response = self.client.post(url, {"title": "sometitle"})
        video = json.loads(response.content)

        self.assertEqual(201, response.status_code) # 201 = resource created
        self.assertEqual(1, Video.objects.all().count())
        self.assertEqual("sometitle", Video.objects.get().title)
        self.assertIn("id", video)
        self.assertIn("title", video)
        self.assertEqual("sometitle", video["title"])

    def test_get_video_upload_url(self):
        url = reverse("api:v1:videoupload-list")

        get_upload_url = lambda: ({'url': 'http://example.com', 'method': 'POST'}, None)
        with override_settings(PLUGINS={"GET_UPLOAD_URL": get_upload_url}):
            response_get = self.client.get(url)
            response_post = self.client.post(url)

        data = response_post.json()
        self.assertEqual(405, response_get.status_code) # method not allowed
        self.assertIn("url", data)
        self.assertIn("method", data)
        self.assertEqual("http://example.com", data["url"])
        self.assertEqual("POST", data["method"])
