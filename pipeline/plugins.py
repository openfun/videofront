import importlib
from django.conf import settings

def load(name):
    """
    Load a plugin based on the PLUGINS[name] setting.

    Raises:
        UndefinedPlugin in case of undefined setting
        ImportError in case of missing module
        MissingPlugin in case of a missing plugin class definition

    """
    setting = settings.PLUGINS.get(name)
    if setting is None:
        raise UndefinedPlugin(name)

    if hasattr(setting, '__call__'):
        plugin_object = setting
    else:
        module_name, object_name = setting.rsplit(".", 1)
        plugin_module = importlib.import_module(module_name)
        plugin_object = getattr(plugin_module, object_name, None)
        if plugin_object is None:
            raise MissingPlugin(name)

    return plugin_object

class UndefinedPlugin(Exception):
    pass

class MissingPlugin(Exception):
    pass
