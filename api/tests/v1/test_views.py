from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.test import TestCase


class ApiV1Tests(TestCase):

    def test_unauthenticated_root(self):
        url = reverse("api:v1:api-root")
        response = self.client.get(url)
        self.assertEqual(200, response.status_code)

    def test_home_redirects_to_api(self):
        url = reverse("home")
        response = self.client.get(url, follow=True)
        self.assertEqual(200, response.status_code)
        self.assertEqual([(reverse('api:v1:api-root'), 302)], response.redirect_chain)

    def test_get_token(self):
        user = User.objects.create(username='testuser')
        user.set_password('password')
        user.save()

        url = reverse("api:v1:auth-token")
        response = self.client.post(url, {
            'username': user.username,
            'password': 'password',
        })
        self.assertEqual(200, response.status_code)
        self.assertEqual(
            {'token': user.auth_token.key},
            response.json()
        )

