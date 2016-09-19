import sys
from .settings import * # pylint: disable=unused-wildcard-import

if len(sys.argv) > 1 and sys.argv[1] == 'test':
    sys.stderr.write("You are running tests with production settings. I'm pretty sure you don't want to do that.\n")
    sys.exit(1)

SECRET_KEY = 'putsomerandomtextherehere'
DEBUG = False
ALLOWED_HOSTS = ['example.com']

CELERY_ALWAYS_EAGER = False

INSTALLED_APPS += ['contrib.plugins.local']
PLUGIN_BACKEND = "contrib.plugins.local.backend.Backend"

# The absolute path to the directory where video assets will be stored
VIDEO_STORAGE_ROOT = '/opt/videofront/storage/'

# Replace by 'avconv' on Ubuntu 14.04
FFMPEG_BINARY = 'ffmpeg'

# Presets are of the form: (
FFMPEG_PRESETS = {
    'HD': {
        'size': '1280x720',
        'video_bitrate': '5120k',
        'audio_bitrate': '384k',
    },
}
