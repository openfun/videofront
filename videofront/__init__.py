# This will make sure the app is always imported when
# Django starts so that shared_task will use this app.
from .celery_videofront import app as celery_app # pylint: disable=unused-import
