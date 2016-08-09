import json
import os

from django.test.utils import override_settings

override_s3_settings = override_settings(
    AWS_ACCESS_KEY_ID='dummyawsaccesskey',
    AWS_SECRET_ACCESS_KEY='dummyawssecretkey',
    AWS_REGION='dummyawsregion',
    S3_PRIVATE_BUCKET='dummys3storagebucket_private',
    S3_PUBLIC_BUCKET='dummys3storagebucket_public',
)

def load_json_fixture(name):
    """
    Load a json fixtures file from the 'fixtures/' directory.
    """
    directory = os.path.join(os.path.dirname(__file__), 'fixtures')
    fixture_path = os.path.join(directory, name)
    return json.load(open(fixture_path))
