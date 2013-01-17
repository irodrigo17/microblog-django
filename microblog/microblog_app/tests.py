from django.test import TestCase
from microblog_app.models import *


class UserTest(TestCase):
    def test_full_name(self):
    	u = User(first_name="John", last_name="Doe")
        self.assertEqual(u.full_name(), "John Doe")
        # TODO: add more tests!

