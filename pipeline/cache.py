import json

from django.core.cache import cache


VIDEO_CACHE_TIMEOUT = 3600

def _cache_key(public_id):
    """
    Key which stores the video content in the cache. Of course, the cache
    must be invalidated every time the video is saved.
    """
    return "VIDEO:" + public_id


def invalidate(public_video_id):
    cache.delete(_cache_key(public_video_id))

def get(public_video_id):
    content = cache.get(_cache_key(public_video_id))
    if content is not None:
        return json.loads(content)
    return None

def set(public_video_id, data):
    return cache.set(_cache_key(public_video_id), json.dumps(data), VIDEO_CACHE_TIMEOUT)
