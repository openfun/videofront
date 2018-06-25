"""
This file includes overrides to build the `development` environment for videofront starting
from the settings of the `production` environment
"""
# pylint: disable=wildcard-import,unused-wildcard-import
from .production import *  # noqa isort:skip

DEBUG = True
CELERY_ALWAYS_EAGER = True
