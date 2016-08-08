import os

from celery import Celery

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'videofront.settings')

# pylint: disable=wrong-import-position
from django.conf import settings

app = Celery('videofront')
app.config_from_object('django.conf:settings')


# Load automatically all tasks from all installed apps. Note that in order to
# call tasks by name, you will have to manually import your task files in your
# app/__init__.py file.
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS) 


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