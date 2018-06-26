"""
Configure Celery to discover tasks from the videofront code base
"""
import os

from django.conf import settings

from celery import Celery

# set the default Django settings module for the 'celery' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "videofront.settings")


APP = Celery("videofront")
APP.config_from_object("django.conf:settings")


# Load automatically all tasks from all installed apps. Note that in order to
# call tasks by name, you will have to manually import your task files in your
# app/__init__.py file.
APP.autodiscover_tasks(lambda: settings.INSTALLED_APPS)


def send_task(name, args=None, kwargs=None, **opts):
    """
    Send a task by name. Contrary to app.send_task, this function respects the
    CELERY_ALWAYS_EAGER settings, which is necessary in tests. As a
    consequence, it works only for registered tasks.
    """
    if settings.CELERY_ALWAYS_EAGER:
        task = APP.tasks[
            name
        ]  # Raises a NotRegistered exception for unregistered tasks
        return task.apply(args=args, kwargs=kwargs, **opts)

    return APP.send_task(name, args=args, kwargs=kwargs)
