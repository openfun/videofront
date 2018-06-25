from django.core.urlresolvers import reverse

from pipeline.tests import factories

from .base import BaseAuthenticatedTests


class PlaylistTests(BaseAuthenticatedTests):
    def test_list_playlists_no_result(self):
        response = self.client.get(reverse("api:v1:playlist-list"))
        playlists = response.json()
        self.assertEqual([], playlists)

    def test_get_playlist(self):
        playlist = factories.PlaylistFactory(
            name="Funkadelic playlist", owner=self.user
        )
        response = self.client.get(
            reverse("api:v1:playlist-detail", kwargs={"id": playlist.public_id})
        )
        result = response.json()

        self.assertEqual(200, response.status_code)
        self.assertEqual("Funkadelic playlist", result["name"])
        self.assertEqual(playlist.public_id, result["id"])

    def test_search_playlist_by_name(self):
        factories.PlaylistFactory(
            name="Funkadelic", owner=self.user, public_id="funkid"
        )
        factories.PlaylistFactory(
            name="Rockabilly", owner=self.user, public_id="rockid"
        )

        response_funk = self.client.get(
            reverse("api:v1:playlist-list"), data={"name": "Funk"}
        )
        playlists_funk = response_funk.json()

        self.assertEqual(1, len(playlists_funk))
        self.assertEqual("funkid", playlists_funk[0]["id"])

    def test_insert_video_in_playlist(self):
        playlist = factories.PlaylistFactory(
            name="Funkadelic playlist", owner=self.user
        )
        factories.VideoFactory(public_id="videoid", owner=self.user)

        response = self.client.post(
            reverse("api:v1:playlist-add-video", kwargs={"id": playlist.public_id}),
            data={"id": "videoid"},
        )

        self.assertEqual(204, response.status_code)
        self.assertEqual(1, playlist.videos.count())

    def test_insert_non_existing_video_in_playlist(self):
        playlist = factories.PlaylistFactory(
            name="Funkadelic playlist", owner=self.user
        )

        response = self.client.post(
            reverse("api:v1:playlist-add-video", kwargs={"id": playlist.public_id}),
            data={"id": "videoid"},
        )

        self.assertEqual(404, response.status_code)

    def test_insert_video_from_different_user_in_playlist(self):
        playlist = factories.PlaylistFactory(
            name="Funkadelic playlist", owner=self.user
        )
        different_user = factories.UserFactory()
        factories.VideoFactory(public_id="videoid", owner=different_user)

        response = self.client.post(
            reverse("api:v1:playlist-add-video", kwargs={"id": playlist.public_id}),
            data={"id": "videoid"},
        )

        self.assertEqual(404, response.status_code)

    def test_remove_video_from_playlist(self):
        playlist = factories.PlaylistFactory(
            name="Funkadelic playlist", owner=self.user
        )
        video = factories.VideoFactory(public_id="videoid", owner=self.user)
        playlist.videos.add(video)

        response = self.client.post(
            reverse("api:v1:playlist-remove-video", kwargs={"id": playlist.public_id}),
            data={"id": "videoid"},
        )

        self.assertEqual(204, response.status_code)
