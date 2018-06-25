import os
from tempfile import NamedTemporaryFile

from django.test import TestCase
from PIL import Image

from pipeline import utils


class UtilsTests(TestCase):
    def test_generate_random_id(self):
        id1 = utils.generate_random_id(1)
        id2 = utils.generate_random_id(2)

        self.assertEqual(1, len(id1))
        self.assertEqual(2, len(id2))

    def test_resize_thumbnail(self):
        def check_size(max_size, expected_width, expected_height):
            img_path = os.path.join(
                os.path.dirname(__file__), "fixtures", "elcapitan.jpg"
            )
            out_img = NamedTemporaryFile(mode="rb", suffix=".jpg")
            utils.resize_image(img_path, out_img.name, max_size)

            resized_image = Image.open(out_img.name)
            self.assertEqual((expected_width, expected_height), resized_image.size)

        check_size(1024, 576, 1024)
        check_size(100, 56, 100)
        check_size(2, 1, 2)

    def test_make_thumbnail(self):
        image = open(
            os.path.join(os.path.dirname(__file__), "fixtures", "elcapitan.jpg"), "rb"
        )
        out_img = NamedTemporaryFile(mode="rb", suffix=".jpg")
        utils.make_thumbnail(image, out_img.name)

        resized_image = Image.open(out_img.name)
        self.assertEqual((576, 1024), resized_image.size)
