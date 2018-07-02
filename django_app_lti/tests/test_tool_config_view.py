import django
from django.conf import settings
from django.core.urlresolvers import reverse, resolve
from django.test import TestCase, RequestFactory
from mock import Mock
from ims_lti_py.tool_config import ToolConfig

from django_app_lti.views import LTIToolConfigView

class ToolConfigViewTest(TestCase):
    def setUp(self):
        django.setup()
        self.view = LTIToolConfigView()
        self.view.request = RequestFactory().get('/lti/config')
        self.view.request.session = {}

    def test_launch_secure_launch_url(self):
        host = "localhost"
        self.view.request.get_host = Mock(return_value=host)
        self.view.request.is_secure = Mock(return_value=True)

        actual = self.view.get_launch_url(self.view.request)
        expected = 'https://' + host + reverse(self.view.LAUNCH_URL)

        self.assertEqual(actual, expected)

    def test_url_excludes_resource_link_id(self):
        test_urls = (
            'https://example.com/lti/launch?resource_link_id=None',
            'https://example.com/lti/launch?resource_link_id=123fabc456',
            'https://example.com/lti/launch?resource_link_id=',
            'https://example.com/lti/launch?resource_link_id',
        )
        expected = 'https://example.com/lti/launch'
        for url in test_urls:
            actual = self.view._url(url)
            self.assertEqual(actual, expected)

    def test_tool_config(self):
        launch_url = "http://foo.bar/"
        self.view.get_launch_url = Mock(return_value=launch_url)

        expected = ToolConfig(
            title=settings.LTI_SETUP.get('TOOL_TITLE'),
            launch_url=launch_url,
            secure_launch_url=launch_url
        )
        actual = self.view.get_tool_config(self.view.request)

        self.assertEqual(actual.title, expected.title)
        self.assertEqual(actual.launch_url, expected.launch_url)
        self.assertEqual(actual.secure_launch_url, expected.secure_launch_url)
