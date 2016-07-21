from django.test.utils import override_settings

override_s3_settings = override_settings(
    AWS_ACCESS_KEY_ID='dummyawsaccesskey',
    AWS_SECRET_ACCESS_KEY='dummyawssecretkey',
    AWS_REGION='dummyawsregion',
    S3_STORAGE_BUCKET='dummys3storagebucket'
)
