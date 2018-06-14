from django.test.utils import override_settings

import pipeline.backend


class TestPluginBackendFactory(object):
    """
    Factory of test plugin backends that implement only a selection of methods.
    """

    def __init__(self, **kwargs):
        self.attributes = kwargs

    def __call__(self):
        backend = TestPluginBackend()
        for name, value in self.attributes.items():
            setattr(backend, name, value)
        return backend


# pylint: disable=abstract-method
class TestPluginBackend(pipeline.backend.BaseBackend):
    pass


def override_plugin_backend(**kwargs):
    """
    Override a selection of methods of the plugin backend, for test purposes.

    Example: @override_plugin_backend(upload_video=lambda x: 42)
    """
    return override_settings(PLUGIN_BACKEND=TestPluginBackendFactory(**kwargs))
