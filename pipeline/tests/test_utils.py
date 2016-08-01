from django.test import TestCase

from pipeline import utils

class UtilsTests(TestCase):

    def test_generate_video_id(self):
        id1 = utils.generate_video_id(1)
        id2 = utils.generate_video_id(2)

        self.assertEqual(1, len(id1))
        self.assertEqual(2, len(id2))
