from .settings import * # pylint: disable=unused-wildcard-import

SECRET_KEY = 'putsomerandomtextherehere'
DEBUG = False
ALLOWED_HOSTS = ['example.com']

CELERY_ALWAYS_EAGER = False

# This is only useful for storing videos on S3
AWS_ACCESS_KEY_ID = 'awsaccesskey'
AWS_SECRET_ACCESS_KEY = 'awssecretaccesskey'
S3_STORAGE_BUCKET = 'bucketforstoringvideos'
AWS_REGION = 'eu-west-1' # http://docs.aws.amazon.com/AWSEC2/latest/UserGuide/using-regions-availability-zones.html#concepts-available-regions
PLUGINS["GET_UPLOAD_URL"] = "contrib.plugins.aws.videoupload.get_upload_url"
INSTALLED_APPS += ['contrib.plugins.aws']
