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
S3_STORAGE_BUCKET = 'bucketforstoringvideos'
ELASTIC_TRANSCODER_PIPELINE_ID = 'yourpipelineid'
ELASTIC_TRANSCODER_PRESETS = {
    'LD': '1351620000001-000030', # System preset: Generic 480p 4:3
    'SD': '1351620000001-000010', # System preset: Generic 720p
    'HD': '1351620000001-000001', # System preset: Generic 1080p
}

# TODO perhaps we can just define a plugin backend from which all plugins will be loaded?
PLUGINS["GET_UPLOAD_URL"] = "contrib.plugins.aws.video.get_upload_url"
PLUGINS["GET_UPLOADED_VIDEO"] = "contrib.plugins.aws.video.get_uploaded_video"
PLUGINS["TRANSCODE_VIDEO"] = "contrib.plugins.aws.video.transcode_video"
PLUGINS["DELETE_RESOURCES"] = "contrib.plugins.aws.video.delete_resources"
