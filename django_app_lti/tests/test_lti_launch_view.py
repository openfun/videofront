import unittest
from braces.views import LoginRequiredMixin
from django.views.generic import RedirectView

from django_app_lti.views import LTILaunchView

class LTILaunchViewTest(unittest.TestCase):
    longMessage = True

    def setUp(self):
        self.view = LTILaunchView()

    def test_view_required_login(self):
        """
        Test that the launch view requires users to log in
        """
        self.assertIsInstance(self.view, LoginRequiredMixin, 'LTI launch view expected to be a subclass of LoginRequiredMixin')
