from django.test import TestCase
from django.test.utils import override_settings

from pipeline import backend


class PipelineBackendTests(TestCase):

    @override_settings(PLUGIN_BACKEND=None)
    def test_undefined_backend(self):
        self.assertRaises(backend.UndefinedPluginBackend, backend.get)

    @override_settings(PLUGIN_BACKEND="undefinedmodule.somewhere")
    def test_missing_plugin_module(self):
        self.assertRaises(ImportError, backend.get)

    @override_settings(PLUGIN_BACKEND="contrib.plugins.some_undefined_function")
    def test_missing_plugin_class(self):
        self.assertRaises(backend.MissingPluginBackend, backend.get)

    @override_settings(PLUGIN_BACKEND=lambda: 42)
    def test_callable_plugin(self):
        dummy = backend.get()

        self.assertIsNotNone(dummy)
        self.assertEqual(42, dummy)

    def test_backend_is_cachable(self):
        backend1 = backend.get()
        backend2 = backend.get()
        self.assertTrue(backend1 is backend2)
