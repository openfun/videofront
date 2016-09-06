from django.contrib.auth.models import User
from django.core.urlresolvers import reverse

from .base import BaseAuthenticatedTests


class UsersTests(BaseAuthenticatedTests):

    def setUp(self):
        super(UsersTests, self).setUp()
        self.user.is_staff = True
        self.user.save()

    def test_get_user(self):
        url = reverse('api:v1:user-detail', kwargs={'username': self.user.username})
        response = self.client.get(url)

        self.assertEqual(200, response.status_code)
        response_data = response.json()

        self.assertNotIn('password', response_data)
        self.assertEqual(self.user.username, response_data['username'])
        self.assertIsNotNone(response_data['token'])

    def test_create_user_with_password(self):
        url = reverse('api:v1:user-list')
        response = self.client.post(url, {
            'username': 'newuser',
            'password': '1234',
        })

        self.assertEqual(201, response.status_code)
        self.assertEqual(1, User.objects.filter(username='newuser').count())
        newuser = User.objects.get(username='newuser')
        self.assertTrue(newuser.check_password('1234'))

    def test_create_user_without_password(self):
        url = reverse('api:v1:user-list')
        response = self.client.post(url, {
            'username': 'newuser',
        })

        self.assertEqual(201, response.status_code)
        self.assertEqual(1, User.objects.filter(username='newuser').count())
        newuser = User.objects.get(username='newuser')

        # Check complex password was used
        self.assertFalse(newuser.check_password('1234'))
        self.assertFalse(newuser.check_password(''))
        self.assertFalse(newuser.check_password(None))

class UsersNonAdminTests(BaseAuthenticatedTests):

    def test_create_user_fails(self):
        url = reverse('api:v1:user-list')
        response = self.client.post(url, {
            'username': 'newuser',
            'password': '1234',
        })

        self.assertEqual(403, response.status_code)
