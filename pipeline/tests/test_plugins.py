from django.test import TestCase
from django.test.utils import override_settings

from pipeline import plugins


class DummyPlugin(object):

    def __init__(self, value):
        self.value = value


class PipelinePluginsTests(TestCase):

    @override_settings(PLUGINS={})
    def test_undefined_plugin(self):
        self.assertRaises(plugins.UndefinedPlugin, plugins.load, "DUMMY")

    @override_settings(PLUGINS={"DUMMY": "undefinedmodule.somewhere"})
    def test_missing_plugin_module(self):
        self.assertRaises(ImportError, plugins.load, "DUMMY")

    @override_settings(PLUGINS={"DUMMY": "contrib.plugins.some_undefined_function"})
    def test_missing_plugin_class(self):
        self.assertRaises(plugins.MissingPlugin, plugins.load, "DUMMY")

    @override_settings(PLUGINS={"DUMMY": lambda: 42})
    def test_callable_plugin(self):
        dummy = plugins.load("DUMMY")

        self.assertIsNotNone(dummy)
        self.assertEqual(42, dummy())

    @override_settings(PLUGINS={"DUMMY": lambda: 42})
    def test_plugins_call(self):
        self.assertEqual(42, plugins.call('DUMMY'))
