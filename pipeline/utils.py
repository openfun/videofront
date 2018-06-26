import os
import random
import string
from tempfile import NamedTemporaryFile

from django.conf import settings

from PIL import Image


def generate_long_random_id():
    return generate_random_id(20)


def generate_random_id(length=12):
    """
    Generate a random video id of given length.
    """
    choices = string.ascii_letters + string.digits
    return "".join([random.choice(choices) for _ in range(0, length)])


def make_thumbnail(file_object, out_path):
    """
    Make a thumbnail with the appropriate size.

    Args:
        file_object (file): must have a 'name' attribute
        out_path (str): destination path
    """
    # Copy source image to temporary file
    img_extension = os.path.splitext(file_object.name)[1]
    src_img = NamedTemporaryFile(mode="wb", suffix=img_extension)
    src_img.write(file_object.read())
    src_img.seek(0)

    resize_image(src_img.name, out_path, settings.THUMBNAILS_SIZE)


def resize_image(in_path, out_path, max_size):
    """
    Resize an image by keeping the aspect ratio such that the maximum of
    (width, height) is equal to max_size. Note that this function may increase
    the size of the input image.

    Args:
        in_path (str): path of the input image file
        out_path (str): path of the output image file
        max_size (int): maximum desired width and height
    """
    in_img = Image.open(in_path)
    ratio = max_size * 1. / max(in_img.size)
    out_img = in_img.resize(
        (round(in_img.size[0] * ratio), round(in_img.size[1] * ratio))
    )
    out_img.save(out_path)
