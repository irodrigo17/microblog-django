from django.test import TestCase
from django.http import HttpRequest
from django.utils import timezone
from copy import copy
from microblog_app.models import *
from microblog_app.api import *
import unittest


class BaseTestCase(TestCase):
    '''
    Base class for tests that adds some initial data to the DB and stores created instances as instance variables.
    '''

    def setUp(self):
        self.u1 = User(username='u1')
        self.u1.save()
        self.u2 = User(username='u2')
        self.u2.save()
        self.u3 = User(username='u3')
        self.u3.save()
        self.u4 = User(username='u4')
        self.u4.save()

        self.p11 = Post(user=self.u1, text='p11')
        self.p11.save()
        self.p12 = Post(user=self.u1, text='p12')
        self.p12.save()
        self.p13 = Post(user=self.u1, text='p13')
        self.p13.save()
        self.p21 = Post(user=self.u2, text='p21')
        self.p21.save()
        self.p22 = Post(user=self.u2, text='p22')
        self.p22.save()
        self.p23 = Post(user=self.u2, text='p23')
        self.p23.save()
        self.p31 = Post(user=self.u3, text='p31')
        self.p31.save()
        self.p32 = Post(user=self.u3, text='p32')
        self.p32.save()
        self.p33 = Post(user=self.u3, text='p33')
        self.p33.save()

        self.f12 = Follow(follower=self.u1, followee=self.u2)
        self.f12.save()
        self.f23 = Follow(follower=self.u2, followee=self.u3)
        self.f23.save()
        self.f24 = Follow(follower=self.u2, followee=self.u4)
        self.f24.save()
        self.f34 = Follow(follower=self.u3, followee=self.u4)
        self.f34.save()

        self.l121 = Like(user=self.u1, post=self.p21)
        self.l121.save()
        self.l221 = Like(user=self.u2, post=self.p21)
        self.l221.save()
        self.l311 = Like(user=self.u3, post=self.p11)
        self.l311.save()

        self.s231 = Share(user=self.u2, post=self.p31)
        self.s231.save()
        self.s411 = Share(user=self.u4, post=self.p11)
        self.s411.save()
        self.s431 = Share(user=self.u4, post=self.p31)
        self.s431.save()

# Model tests

class UserTest(BaseTestCase):

    def test_full_name(self):
    	u = User(first_name="John", last_name="Doe")
        self.assertEqual("John Doe", u.full_name())
    
    def test_following_count(self):
    	self.assertEqual(1, self.u1.following_count())
    	self.assertEqual(2, self.u2.following_count())
    	self.assertEqual(1, self.u3.following_count())
    	self.assertEqual(0, self.u4.following_count())
    
    def test_follwers_count(self):
        self.assertEqual(0, self.u1.followers_count())
        self.assertEqual(1, self.u2.followers_count())
        self.assertEqual(1, self.u3.followers_count())
        self.assertEqual(2, self.u4.followers_count())

    def test_posts_count(self):
        self.assertEqual(3, self.u1.posts_count())
        self.assertEqual(3, self.u2.posts_count())
        self.assertEqual(3, self.u3.posts_count())
        self.assertEqual(0, self.u4.posts_count())


    def test_unicode(self):
    	self.assertEqual('u1', self.u1.__unicode__())

    def test_set_password(self):
        with self.assertRaises(ValidationError):
            self.u1.set_password('')
        with self.assertRaises(ValidationError):
            self.u1.set_password('1')
        with self.assertRaises(ValidationError):
            self.u1.set_password('12')
        with self.assertRaises(ValidationError):
            self.u1.set_password('123')

        self.u1.set_password('1234')


class PostTest(BaseTestCase):

    def test_liked_by_count(self):
        self.assertEqual(2, self.p21.liked_by_count())
        self.assertEqual(1, self.p11.liked_by_count())
        self.assertEqual(0, self.p12.liked_by_count())
    
    def test_shared_by_count(self):
        self.assertEqual(2, self.p31.shared_by_count())
        self.assertEqual(0, self.p32.shared_by_count())
        self.assertEqual(1, self.p11.shared_by_count())
    
    def test_replies_count(self):
        self.assertEqual(0, self.p11.replies_count())

    def test_unicode(self):
        self.assertEqual('p11', self.p11.__unicode__())

    @unittest.skip("max_length validation is not enforced in SQLite")
    def test_text_validation(self):
        # text field should be 200 characters or less
        user = User(username='test-post-validations-user')
        user.save()
        post = Post(user=user, text='Testing posts validations')
        post.save()

        limit_post = Post(user=user, text="x" * 200)
        limit_post.save()

        bad_post = Post(user=user, text="x"*201)
        try:
            bad_post.save()
            self.fail("Save should have failed, text is %i characters long" % len(bad_post.text))
        except ValidationError as error:
            pass

    def test_auto_dates(self):
        # crate a post
        user = User(username='test-post-auto-dates-user')
        user.save()
        post = Post(user=user, text='Testing posts auto dates')
        before = timezone.now()
        post.save()
        after = timezone.now()
        self.assertTrue(timezone.is_aware(post.created_date))
        self.assertTrue(timezone.is_aware(post.modified_date))
        self.assertTrue(before < post.created_date < after)
        self.assertTrue(before < post.modified_date < after)
        # update post
        post.text = 'Updated text'
        old_created_date = copy(post.created_date)
        old_modified_date = copy(post.modified_date)
        before = timezone.now()
        post.save()
        after = timezone.now()
        self.assertTrue(timezone.is_aware(post.created_date))
        self.assertTrue(timezone.is_aware(post.modified_date))
        self.assertTrue(before < post.modified_date < after)
        self.assertTrue(old_modified_date < post.modified_date)
        self.assertTrue(old_created_date == post.created_date)


class FollowTest(BaseTestCase):

    def test_non_reflexive(self):
        follow = Follow(follower=self.u1, followee=self.u1)
        try:
            follow.save()
            self.fail('Follow relation should be non-reflexive')
        except ValidationError as error:
            pass

    def test_non_symmetrical(self):
        self.assertTrue(self.u1.following.filter(followee=self.u2).exists())
        self.assertFalse(self.u2.following.filter(followee=self.u1).exists())
        self.assertFalse(self.u1.followed_by.filter(follower=self.u2).exists())
        self.assertTrue(self.u2.followed_by.filter(follower=self.u1).exists())

    def test_unique_together(self):
        follow = Follow(follower=self.u1, followee=self.u2)
        try:
            follow.save()
            self.fail('follower and followee should be unique_together')
        except IntegrityError:
            pass


class LikeTest(BaseTestCase):

    def test_unicode(self):
        self.assertEquals(self.l121.__unicode__(), 'u1 likes p21')


class ShareTest(BaseTestCase):

    def test_unicode(self):
        self.assertEquals(self.s231.__unicode__(), 'u2 shares p31')


class FeedResourceTest(BaseTestCase):
    
    def test_apply_authorization_limits(self):
        request = HttpRequest() # request mock
        request.user = self.u1
        object_list = Post.objects.all() # object_list mock
        feed_resource = FeedResource()
        feed = feed_resource.apply_authorization_limits(request,object_list)
        expected_result = [self.p11, self.p12, self.p13, self.p21, self.p22, self.p23, self.p31]
        self.assertEqual(expected_result, list(feed))


