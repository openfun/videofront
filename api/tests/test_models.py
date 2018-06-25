from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.authtoken.models import Token


class ApiV1ModelsTests(TestCase):
    def test_tokens_are_created_for_all_users(self):
        user = User.objects.create(username="testuser")
        self.assertEqual(1, Token.objects.filter(user=user).count())
