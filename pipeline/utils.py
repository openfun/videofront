import random
import string

def generate_random_id(length=12):
    """
    Generate a random video id of given length.
    """
    choices = string.ascii_letters + string.digits
    return ''.join([random.choice(choices) for _ in range(0, length)])
