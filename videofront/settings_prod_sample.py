from .settings import * # pylint: disable=unused-wildcard-import

SECRET_KEY = 'putsomerandomtextherehere'
DEBUG = False
ALLOWED_HOSTS = ['example.com']

CELERY_ALWAYS_EAGER = False

# This is only useful for storing videos on S3
INSTALLED_APPS += ['contrib.plugins.aws']

AWS_ACCESS_KEY_ID = 'awsaccesskey'
AWS_SECRET_ACCESS_KEY = 'awssecretaccesskey'
AWS_REGION = 'eu-west-1' # http://docs.aws.amazon.com/AWSEC2/latest/UserGuide/using-regions-availability-zones.html#concepts-available-regions

# This is the bucket that will store all video assets.
S3_BUCKET = 's3bucket'

ELASTIC_TRANSCODER_PIPELINE_ID = 'yourpipelineid'
ELASTIC_TRANSCODER_PRESETS = {
    'LD': '1351620000001-000030', # System preset: Generic 480p 4:3
    'SD': '1351620000001-000010', # System preset: Generic 720p
    'HD': '1351620000001-000001', # System preset: Generic 1080p
}

PLUGIN_BACKEND = "contrib.plugins.aws.backend.Backend"
