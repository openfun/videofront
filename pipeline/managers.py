from time import time

from django.db import models


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

    def obsolete(self):
        """
        Unused upload urls that have expired.
        """
        return self.filter(expires_at__lt=time() - 2*self.EXPIRE_DELAY, was_used=False)
