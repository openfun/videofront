import json
from time import time

from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.test import TestCase
from mock import Mock

from pipeline import models
from pipeline.tests.utils import override_plugin_backend


class VideosUnauthenticatedTests(TestCase):

    def test_list_videos(self):
        url = reverse("api:v1:video-list")
        response = self.client.get(url)
        # BasicAuthentication returns a 401 in case
        self.assertEqual(401, response.status_code)


class BaseAuthenticatedTests(TestCase):

    def setUp(self):
        user = User.objects.create(username="test", is_active=True)
        user.set_password("password")
        user.save()
        self.client.login(username="test", password="password")


class VideoUploadUrlTests(BaseAuthenticatedTests):

    def test_obtain_video_upload_url(self):
        url = reverse("api:v1:videoupload-list")

        create_upload_url = Mock(return_value={
            'url': 'http://example.com',
            'method': 'POST',
            'id': 'videoid',
            'expires_at': 0,
        })
        with override_plugin_backend(create_upload_url=create_upload_url):
            response = self.client.post(url, {'filename': 'Some file.mp4'})

        self.assertEqual(200, response.status_code)
        upload_url = response.json()
        create_upload_url.assert_called_once_with('Some file.mp4')
        self.assertIn("url", upload_url)
        self.assertEqual("http://example.com", upload_url["url"])
        self.assertIn("method", upload_url)
        self.assertEqual("POST", upload_url["method"])


    def test_get_fails_on_videoupload(self):
        url = reverse("api:v1:videoupload-list")
        response = self.client.get(url)
        self.assertEqual(405, response.status_code) # method not allowed


class VideosTests(BaseAuthenticatedTests):

    def test_list_videos(self):
        url = reverse("api:v1:video-list")
        # TODO test video list requires just one query
        response = self.client.get(url)
        videos = response.json()

        self.assertEqual(200, response.status_code)
        self.assertEqual([], videos)

    def test_get_video(self):
        video = models.Video.objects.create(public_id='videoid', title="Some title")
        models.VideoTranscoding(video=video, status=models.VideoTranscoding.STATUS_SUCCESS)
        response = self.client.get(reverse('api:v1:video-detail', kwargs={'id': 'videoid'}))
        self.assertEqual(200, response.status_code)
        video = response.json()

        self.assertEqual('videoid', video['id'])
        self.assertEqual('Some title', video['title'])
        self.assertEqual([], video['subtitles'])

    def test_get_not_processing_video(self):
        models.Video.objects.create(public_id="videoid", title='videotitle')
        url = reverse("api:v1:video-list")
        videos = self.client.get(url).json()

        self.assertEqual(1, len(videos))
        self.assertEqual('videoid', videos[0]['id'])
        self.assertEqual('videotitle', videos[0]['title'])
        self.assertIn('status_details', videos[0])
        self.assertEqual(None, videos[0]['status_details'])

    def test_get_processing_video(self):
        video = models.Video.objects.create(public_id="videoid", title='videotitle')
        _transcoding = models.VideoTranscoding.objects.create(
            video=video,
            progress=42,
            status=models.VideoTranscoding.STATUS_PROCESSING
        )
        videos = self.client.get(reverse("api:v1:video-list")).json()

        self.assertEqual('processing', videos[0]['status_details']['status'])
        self.assertEqual(42, videos[0]['status_details']['progress'])

    def test_list_failed_videos(self):
        video = models.Video.objects.create(public_id="videoid", title='videotitle')
        _transcoding = models.VideoTranscoding.objects.create(
            video=video,
            status=models.VideoTranscoding.STATUS_FAILED
        )

        videos = self.client.get(reverse("api:v1:video-list")).json()
        self.assertEqual([], videos)

    def test_create_video_fails(self):
        url = reverse("api:v1:video-list")
        response = self.client.post(
            url,
            {
                "public_id": "videoid",
                "title": "sometitle"
            }
        )
        self.assertEqual(405, response.status_code) # method not allowed

    @override_plugin_backend(
        get_uploaded_video=lambda video_id: None,
        transcode_video=lambda video_id: [],
    )
    def test_get_video_that_was_just_uploaded(self):
        models.VideoUploadUrl.objects.create(
            public_video_id="videoid",
            expires_at=time() + 3600
        )
        response = self.client.get(reverse("api:v1:video-detail", kwargs={'id': 'videoid'}))

        self.assertEqual(200, response.status_code)

    def test_update_video_title(self):
        models.Video.objects.create(public_id="videoid", title="title1")
        response = self.client.put(
            reverse('api:v1:video-detail', kwargs={'id': 'videoid'}),
            data=json.dumps({'title': 'title2'}),
            content_type='application/json'
        )
        self.assertEqual(200, response.status_code)
        self.assertEqual('title2', models.Video.objects.get().title)

    def test_delete_video(self):
        mock_delete_resources = Mock()
        models.Video.objects.create(public_id="videoid")
        with override_plugin_backend(delete_resources=mock_delete_resources):
            response = self.client.delete(reverse('api:v1:video-detail', kwargs={'id': 'videoid'}))

        self.assertEqual(204, response.status_code)
        self.assertEqual(0, models.Video.objects.count())
        mock_delete_resources.assert_called_once_with('videoid')

    def test_get_video_with_subtitles(self):
        video = models.Video.objects.create(public_id="videoid")
        video.subtitles.create(language="fr", public_id="subid1")
        video.subtitles.create(language="en", public_id="subid2")

        video = self.client.get(reverse("api:v1:video-detail", kwargs={'id': 'videoid'})).json()
        self.assertEqual([
            {
                'id': 'subid1',
                'language': 'fr'
            },
            {
                'id': 'subid2',
                'language': 'en'
            },
        ], video['subtitles'])
