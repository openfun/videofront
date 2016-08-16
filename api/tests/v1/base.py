from django.test import TestCase
from django.contrib.auth.models import User


class BaseAuthenticatedTests(TestCase):

    def setUp(self):
        self.user = User.objects.create(username="test", is_active=True)
        self.user.set_password("password")
        self.user.save()
        self.client.login(username="test", password="password")
