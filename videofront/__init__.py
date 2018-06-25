"""
This will make sure the app is always imported when Django starts so that shared_task will use
this app.
"""
# pylint: disable=unused-import
from .celery_videofront import APP  # noqa
