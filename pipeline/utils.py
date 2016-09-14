import random
import string

from PIL import Image

def generate_random_id(length=12):
    """
    Generate a random video id of given length.
    """
    choices = string.ascii_letters + string.digits
    return ''.join([random.choice(choices) for _ in range(0, length)])

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
    out_img = in_img.resize((round(in_img.size[0] * ratio), round(in_img.size[1] * ratio)))
    out_img.save(out_path)
