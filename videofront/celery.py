from __future__ import absolute_import

import os

from celery import Celery

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'videofront.settings')

# pylint: disable=wrong-import-position
from django.conf import settings

app = Celery('videofront')

# Using a string here means the worker will not have to
# pickle the object when using Windows.
app.config_from_object('django.conf:settings')
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS) # TODO do we really want to load all tasks from all apps?


# TODO do we want to keep this function?
def send_task_if_registered(name, args=None, kwargs=None, **opts):
    """
    Send a task if it was registered. This is useful for optional tasks that
    might not be implemented by all plugins.
    """
    if name in app.tasks:
        return send_task(name, args=args, kwargs=kwargs, **opts)

# TODO do we want to keep this function?
def send_task(name, args=None, kwargs=None, **opts):
    """
    Send a task by name. Contrary to app.send_task, this function respects the
    CELERY_ALWAYS_EAGER settings, which is necessary in tests. As a
    consequence, it works only for registered tasks.
    """
    if settings.CELERY_ALWAYS_EAGER:
        task = app.tasks[name] # Raises a NotRegistered exception for unregistered tasks
        return task.apply(args=args, kwargs=kwargs, **opts)
    else:
        return app.send_task(name, args=args, kwargs=kwargs)

@app.task(bind=True)
def debug_task(self):
    print('Request: {0!r}'.format(self.request))
