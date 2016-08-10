import sys
from .settings import * # pylint: disable=unused-wildcard-import

if len(sys.argv) > 0 and sys.argv[1] == 'test':
    sys.stderr.write("You are running tests with production settings. I'm pretty sure you don't want to do that.\n")
    sys.exit(1)

SECRET_KEY = 'putsomerandomtextherehere'
DEBUG = False
ALLOWED_HOSTS = ['example.com']

CELERY_ALWAYS_EAGER = False

# This is only useful for storing videos on S3
INSTALLED_APPS += ['contrib.plugins.aws']
PLUGIN_BACKEND = "contrib.plugins.aws.backend.Backend"

AWS_ACCESS_KEY_ID = 'awsaccesskey'
AWS_SECRET_ACCESS_KEY = 'awssecretaccesskey'
AWS_REGION = 'eu-west-1' # http://docs.aws.amazon.com/AWSEC2/latest/UserGuide/using-regions-availability-zones.html#concepts-available-regions

# This is the bucket that will store all video assets.
S3_BUCKET = 's3bucket'

# Presets are of the form: (name, ID, bitrate)
ELASTIC_TRANSCODER_PRESETS = [
    ('LD', '1351620000001-000030', 900),  # System preset: Generic 480p 4:3
    ('SD', '1351620000001-000010', 2400), # System preset: Generic 720p
    ('HD', '1351620000001-000001', 5400), # System preset: Generic 1080p
]
ELASTIC_TRANSCODER_PIPELINE_ID = 'yourpipelineid'
