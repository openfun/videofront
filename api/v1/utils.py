import random
import string


def random_password(length=20):
    """
    Return a random password of given length.
    """
    return "".join([random.choice(string.printable) for _ in range(0, length)])
