import mock

from django.conf import settings


def override_plugins(**kwargs):
    return mock.patch.dict(settings.PLUGINS, kwargs)
