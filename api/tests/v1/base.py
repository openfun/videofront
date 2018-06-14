from django.contrib.auth.models import User
from django.test import TestCase


class BaseAuthenticatedTests(TestCase):
    def setUp(self):
        self.user = User.objects.create(username="test", is_active=True)
        self.user.set_password("password")
        self.user.save()
        self.client.login(username="test", password="password")
