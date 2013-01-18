from django.test import TestCase
from microblog_app.models import *


class UserTest(TestCase):
    def test_full_name(self):
    	u = User(first_name="John", last_name="Doe")
        self.assertEqual("John Doe", u.full_name())
    
    def test_following_count(self):
    	# create users
    	u1 = User(username='u1')
    	u1.save()
    	self.assertEqual(0, u1.following_count())
    	u2 = User(username='u2')
    	u2.save()
    	self.assertEqual(0, u2.following_count())
    	u3 = User(username='u3')
    	u3.save()
    	self.assertEqual(0, u3.following_count())

    	# create some follows
    	f12 = Follow(follower=u1, followee=u2)
    	f12.save()
    	self.assertEqual(1, u1.following_count())
    	self.assertEqual(0, u1.followers_count())
    	self.assertEqual(0, u2.following_count())
    	self.assertEqual(1, u2.followers_count())
    	f13 = Follow(follower=u1, followee=u3)
    	f13.save()
    	self.assertEqual(2, u1.following_count())
    	self.assertEqual(0, u2.following_count())
    	self.assertEqual(0, u3.following_count())
    	self.assertEqual(0, u1.followers_count())
    	self.assertEqual(1, u2.followers_count())
    	self.assertEqual(1, u3.followers_count())


    def test_unicode(self):
    	u1 = User(username='u1')
    	self.assertEqual('u1', u1.__unicode__())
