import unittest
from scripts.cap256_launch.train_mixture import validate_exposure


class ExposureTests(unittest.TestCase):
    def setUp(self):
        self.original=['o%d'%i for i in range(256)]
        self.additional=['a%d'%i for i in range(256)]

    def test_equal_updates_different_exposure(self):
        validate_exposure(self.original*40,self.original,self.additional,'repeat256')
        validate_exposure((self.original+self.additional)*20,self.original,self.additional,'diverse512')

    def test_dev_leak_rejected(self):
        schedule=(self.original+self.additional)*20
        schedule[-1]='dev-heldout'
        with self.assertRaises(ValueError):
            validate_exposure(schedule,self.original,self.additional,'diverse512')

    def test_wrong_repetition_rejected(self):
        with self.assertRaises(ValueError):
            validate_exposure(self.original*40,self.original,self.additional,'diverse512')


if __name__=='__main__':unittest.main()
