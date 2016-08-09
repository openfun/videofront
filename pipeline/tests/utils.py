from django.test.utils import override_settings

import pipeline.backend


class TestPluginBackendFactory(object):

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
    # TODO document this
    return override_settings(PLUGIN_BACKEND=TestPluginBackendFactory(**kwargs))
