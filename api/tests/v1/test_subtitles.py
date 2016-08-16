from io import StringIO

from django.core.urlresolvers import reverse
from django.test.utils import override_settings
from mock import Mock, patch

from pipeline import models
from pipeline.tests.utils import override_plugin_backend
from pipeline.tests import factories

from .base import BaseAuthenticatedTests


class VideoSubtitlesTests(BaseAuthenticatedTests):

    @override_plugin_backend(
        upload_subtitles=lambda *args: None,
        get_subtitles_download_url=lambda *args: "http://example.com/subs.vtt"
    )
    def test_upload_subtitles(self):
        video = factories.VideoFactory(public_id="videoid", owner=self.user)
        url = reverse("api:v1:video-subtitles", kwargs={'id': 'videoid'})
        subfile = StringIO("some srt content in here")
        response = self.client.post(
            url,
            data={
                'language': 'fr',
                'name': 'subs.srt', 'attachment': subfile
            },
        )

        self.assertEqual(201, response.status_code)
        subtitles = response.json()
        self.assertLess(0, len(subtitles["id"]))
        self.assertEqual("fr", subtitles["language"])
        self.assertEqual("http://example.com/subs.vtt", subtitles["download_url"])
        self.assertEqual(1, video.subtitles.count())

    def test_upload_subtitles_invalid_language(self):
        factories.VideoFactory(public_id="videoid", owner=self.user)
        url = reverse("api:v1:video-subtitles", kwargs={'id': 'videoid'})
        # only country codes are accepted
        response = self.client.post(url, data={'language': 'french'})

        self.assertEqual(400, response.status_code)
        self.assertIn('language', response.json())
        self.assertEqual(0, models.VideoSubtitles.objects.count())

    def test_upload_subtitles_missing_attachment(self):
        factories.VideoFactory(public_id="videoid", owner=self.user)
        url = reverse("api:v1:video-subtitles", kwargs={'id': 'videoid'})
        response = self.client.post(url, data={'language': 'fr'})

        self.assertEqual(400, response.status_code)
        self.assertIn('attachment', response.json())
        self.assertEqual(0, models.VideoSubtitles.objects.count())

    @patch('django.core.handlers.base.logger')# mute request logger
    def test_upload_subtitles_failed_upload(self, mock_logger):
        factories.VideoFactory(public_id="videoid", owner=self.user)
        url = reverse("api:v1:video-subtitles", kwargs={'id': 'videoid'})
        subfile = StringIO("some srt content in here")

        upload_subtitles = Mock(side_effect=ValueError)
        with override_plugin_backend(upload_subtitles=upload_subtitles):
            self.assertRaises(ValueError, self.client.post, url,
                data={
                    'language': 'fr',
                    'name': 'subs.srt', 'attachment': subfile
                },
            )

        self.assertEqual(0, models.VideoSubtitles.objects.count())

    def test_cannot_modify_subtitles(self):
        video = factories.VideoFactory(public_id="videoid", owner=self.user)
        video.subtitles.create(public_id="subsid", language="fr")
        url = reverse("api:v1:video-subtitles", kwargs={'id': 'videoid'})
        subfile = StringIO("some srt content in here")

        with override_plugin_backend(
                upload_subtitles=lambda *args: None,
                get_subtitles_download_url=lambda *args: None
        ):
            response = self.client.post(url, data={
                'id': 'subsid',
                'language': 'en',
                'name': 'subs.srt', 'attachment': subfile
            })

        # Subtitles were in fact created, not modified
        self.assertEqual(201, response.status_code)
        self.assertEqual('fr', video.subtitles.get(public_id='subsid').language)
        self.assertEqual('en', video.subtitles.exclude(public_id='subsid').get().language)

    @override_settings(SUBTITLES_MAX_BYTES=139)
    def test_upload_subtitles_too_large(self):
        factories.VideoFactory(public_id="videoid", owner=self.user)
        content = (
            "Some vtt content here. This should as long as a tweet, at"
            " 140 characters exactly. Yes, I counted, multiple times and came up with"
            " 140 chars."
        )
        subfile = StringIO(content)
        self.assertEqual(140, len(content))
        url = reverse("api:v1:video-subtitles", kwargs={'id': 'videoid'})

        response = self.client.post(url, data={
            'language': 'en',
            'name': 'subs.srt', 'attachment': subfile
        })
        self.assertEqual(400, response.status_code)
        self.assertIn('attachment', response.json())
        self.assertIn('139', response.json()['attachment'])
