from django.core.urlresolvers import reverse
from mock import Mock

from pipeline import models
from pipeline.tests.utils import override_plugin_backend
from pipeline.tests import factories
from .base import BaseAuthenticatedTests


class VideoUploadUrlTests(BaseAuthenticatedTests):

    def setUp(self):
        super(VideoUploadUrlTests, self).setUp()
        self.create_upload_url = Mock(return_value={
            'url': 'http://example.com',
            'method': 'POST',
            'id': 'videoid',
            'expires_at': 0,
        })

    def test_obtain_video_upload_url(self):
        url = reverse("api:v1:videoupload-list")

        with override_plugin_backend(create_upload_url=self.create_upload_url):
            response = self.client.post(url, {'filename': 'Some file.mp4'})

        self.assertEqual(200, response.status_code)
        upload_url = response.json()
        self.create_upload_url.assert_called_once_with('Some file.mp4')
        self.assertIn("url", upload_url)
        self.assertEqual("http://example.com", upload_url["url"])
        self.assertIn("method", upload_url)
        self.assertEqual("POST", upload_url["method"])
        self.assertEqual(1, models.VideoUploadUrl.objects.count())
        self.assertEqual(self.user, models.VideoUploadUrl.objects.get().owner)


    def test_get_fails_on_videoupload(self):
        url = reverse("api:v1:videoupload-list")
        response = self.client.get(url)
        self.assertEqual(405, response.status_code) # method not allowed

    def test_obtain_video_upload_url_with_playlist_id(self):
        playlist = factories.PlaylistFactory(owner=self.user)
        with override_plugin_backend(create_upload_url=self.create_upload_url):
            self.client.post(reverse("api:v1:videoupload-list"), {
                'playlist_id': playlist.public_id,
                'filename': 'Some file.mp4'
            })

        self.assertEqual(playlist, models.VideoUploadUrl.objects.get().playlist)


    def test_obtain_video_upload_url_with_invalid_playlist_id(self):
        with override_plugin_backend(create_upload_url=self.create_upload_url):
            response = self.client.post(reverse("api:v1:videoupload-list"), {
                'playlist_id': 'dummy_id',
                'filename': 'Some file.mp4'
            })

        self.assertEqual(400, response.status_code)

    def test_obtain_video_upload_url_with_unauthorized_playlist_id(self):
        # Create factory from different owner
        playlist = factories.PlaylistFactory()

        with override_plugin_backend(create_upload_url=self.create_upload_url):
            response = self.client.post(reverse("api:v1:videoupload-list"), {
                'playlist_id': playlist.public_id,
                'filename': 'Some file.mp4'
            })

        self.assertEqual(400, response.status_code)
