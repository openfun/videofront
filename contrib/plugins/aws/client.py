from django.conf import settings

import boto3


def s3_client():
    return session().client('s3', region_name=settings.AWS_REGION)

def session():
    """
    Boto3 authenticated session
    """
    return boto3.Session(
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
    )
