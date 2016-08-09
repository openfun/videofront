from django.test import TestCase
from django.test.utils import override_settings

from pipeline import plugins


class DummyPlugin(object):

    def __init__(self, value):
        self.value = value


class PipelinePluginsTests(TestCase):

    @override_settings(PLUGIN_BACKEND=None)
    def test_undefined_plugin(self):
        self.assertRaises(plugins.UndefinedPluginBackend, plugins.load)

    @override_settings(PLUGIN_BACKEND="undefinedmodule.somewhere")
    def test_missing_plugin_module(self):
        self.assertRaises(ImportError, plugins.load)

    @override_settings(PLUGIN_BACKEND="contrib.plugins.some_undefined_function")
    def test_missing_plugin_class(self):
        self.assertRaises(plugins.MissingPluginBackend, plugins.load)

    @override_settings(PLUGIN_BACKEND=lambda: 42)
    def test_callable_plugin(self):
        dummy = plugins.load()

        self.assertIsNotNone(dummy)
        self.assertEqual(42, dummy)
