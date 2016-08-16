from django.core.urlresolvers import reverse

from pipeline.tests import factories
from .base import BaseAuthenticatedTests


class PlaylistTests(BaseAuthenticatedTests):

    def test_list_playlists_no_result(self):
        response = self.client.get(reverse('api:v1:playlist-list'))
        playlists = response.json()
        self.assertEqual([], playlists)

    def test_get_playlist(self):
        playlist = factories.PlaylistFactory(name="Funkadelic playlist", owner=self.user)
        response = self.client.get(reverse('api:v1:playlist-detail', kwargs={'id': playlist.public_id}))
        result = response.json()

        self.assertEqual(200, response.status_code)
        self.assertEqual("Funkadelic playlist", result["name"])
        self.assertEqual(playlist.public_id, result["id"])

    def test_search_playlist_by_name(self):
        factories.PlaylistFactory(name="Funkadelic", owner=self.user, public_id="funkid")
        factories.PlaylistFactory(name="Rockabilly", owner=self.user, public_id="rockid")

        response_funk = self.client.get(reverse('api:v1:playlist-list'), data={'name': 'Funk'})
        playlists_funk = response_funk.json()

        self.assertEqual(1, len(playlists_funk))
        self.assertEqual('funkid', playlists_funk[0]['id'])
