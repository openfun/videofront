from time import time

from django.db import models
from django.db.models import Q


class VideoUploadUrlManager(models.Manager):
    # We consider that once an upload url has been created, it is valid for 1h
    # after it has expired in order to take into account the time it takes for
    # the upload to finish.
    EXPIRE_DELAY = 3600

    def available(self):
        """
        Filter out unavailable objects.
        """
        return self.filter(expires_at__gt=time() - self.EXPIRE_DELAY, was_used=False)

    def should_check(self):
        """
        Return upload urls for which we should check whether they have been used or not.
        """
        # TODO remove this
        return self.filter(
            Q(
                expires_at__gt=time() - self.EXPIRE_DELAY,
                was_used=False
            ) | Q(
                last_checked__isnull=True
            )
        )
