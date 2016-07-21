from django.core.urlresolvers import reverse
from django.test import TestCase


class ApiV1TestCase(TestCase):

    def test_unauthenticated_root(self):
        url = reverse("api:v1:api-root")
        response = self.client.get(url)
        self.assertEqual(200, response.status_code)

    def test_home_redirects_to_api(self):
        url = reverse("home")
        response = self.client.get(url, follow=True)
        self.assertEqual(200, response.status_code)
        self.assertEqual([(reverse('api:v1:api-root'), 302)], response.redirect_chain)
