import importlib
from django.conf import settings

def load():
    """
    Load a plugin backend based on the PLUGIN_BACKEND setting.

    Raises:
        UndefinedPluginBackend in case of undefined setting
        ImportError in case of missing module
        MissingPluginBackend in case of a missing plugin class definition

    """
    setting = getattr(settings, 'PLUGIN_BACKEND')
    if setting is None:
        raise UndefinedPluginBackend()

    if hasattr(setting, '__call__'):
        backend_object = setting()
    else:
        module_name, object_name = setting.rsplit(".", 1)
        backend_module = importlib.import_module(module_name)
        backend_class = getattr(backend_module, object_name, None)
        if backend_class is None:
            raise MissingPluginBackend(setting)
        # TODO we should cache the plugin backend across calls
        backend_object = backend_class()

    return backend_object

class UndefinedPluginBackend(Exception):
    pass

class MissingPluginBackend(Exception):
    pass
