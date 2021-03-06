'''
Unit tests for BlendedProfileBuilder
'''
import unittest
from profile_builder import BlendedProfileBuilder

class TestBlendedProfileBuilder(unittest.TestCase):

    def setUp(self):
        self.builder = BlendedProfileBuilder('AHS','AWB',0.5,0.5)

    def test_load_processed_profile(self):
        self.assertEqual(3, len(self.builder.load_processed_profile('AHS').columns))

    # additional tests to be added below ...

if __name__ == '__main__':
    unittest.main()
