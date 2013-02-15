from django.test import TestCase
from django.http import HttpRequest
from django.utils import timezone
from tastypie.models import ApiKey
from copy import copy
from microblog_app.models import *
from microblog_app.api import *
import unittest


class BaseTestCase(TestCase):
    '''
    Base class for tests that adds some initial data to the DB and stores created instances as instance variables.
    '''

    def setUp(self):
        self.u1 = User(username='u1', email='u1@email.com')
        self.u1.save()
        self.u2 = User(username='u2', email='u2@email.com')
        self.u2.save()
        self.u3 = User(username='u3', email='u3@email.com')
        self.u3.save()
        self.u4 = User(username='u4', email='u4@email.com')
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
        self.assertTrue(self.u1.check_password('1234'))

    def test_followers(self):
        self.assertEquals([self.u2, self.u3], list(self.u4.followers.all()))
        self.assertEquals([self.u2], list(self.u3.followers.all()))
        self.assertEquals([self.u1], list(self.u2.followers.all()))
        self.assertEquals([], list(self.u1.followers.all()))

    def test_follows(self):
        self.assertEquals([self.u2], list(self.u1.follows.all()))
        self.assertEquals([self.u3, self.u4], list(self.u2.follows.all()))
        self.assertEquals([self.u4], list(self.u3.follows.all()))
        self.assertEquals([], list(self.u4.follows.all()))


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
        self.assertTrue(self.u1.follows_follower.filter(followee=self.u2).exists())
        self.assertFalse(self.u2.follows_follower.filter(followee=self.u1).exists())
        self.assertFalse(self.u1.follows_followee.filter(follower=self.u2).exists())
        self.assertTrue(self.u2.follows_followee.filter(follower=self.u1).exists())

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


class LostPasswordTest(BaseTestCase):

    def test_save(self): # TODO: mock email service someway so tests don't deppend on it
        # bad email, no password
        try:
            LostPassword(email='bad@email.com').save()
            self.fail('Should have thrown an exception if no user with the given email')
        except User.DoesNotExist:
            pass

        # bad email, set password
        try:
            LostPassword(email='bad@email.com', new_password='password').save()
            self.fail('Should have thrown an exception if no user with the given email')
        except User.DoesNotExist:
            pass

        # good email, no password
        lost_password = LostPassword(email='u1@email.com')
        lost_password.save()
        self.assertTrue(lost_password.id > 0)
        self.assertTrue(len(lost_password.uuid) > 0)
        self.assertEquals(1, LostPassword.objects.count())

        lost_password = LostPassword(email='u1@email.com')
        lost_password.save()
        self.assertTrue(lost_password.id > 0)
        self.assertTrue(len(lost_password.uuid) > 0)
        self.assertEquals(1, LostPassword.objects.count(), "Any previous instances for the same email should be deleted")

        # good email, set password
        user = User(username='lost_password', email='lost_password@email.com')
        user.set_password('1234')
        user.save()
        lost_password = LostPassword(email=user.email)
        lost_password.save()
        self.assertEquals(2, LostPassword.objects.count())
        lost_password.new_password = 'pass'
        lost_password.save()
        user = User.objects.get(pk=user.pk)
        self.assertTrue(user.check_password(lost_password.new_password))
        self.assertEquals(1, LostPassword.objects.count())
        self.assertEquals(0, LostPassword.objects.filter(email=user.email).count(), "Any instances with the given email should have been deleted")



# API tests

class PostResourceTest(BaseTestCase):
    
    def test_get_feed(self):
        request = HttpRequest() # request mock
        request.user = self.u1
        post_resource = PostResource()
        feed = post_resource.get_feed(request)
        expected_result = [self.p11, self.p12, self.p13, self.p21, self.p22, self.p23, self.p31]
        self.assertEqual(expected_result, list(feed))


class MicroblogApiKeyAuthenticationTest(BaseTestCase):
    
    def api_key(self, user):
        return ApiKey.objects.get(user=user).key        

    def test_header_authorization(self):
        # authorized
        request = HttpRequest()
        user = self.u1
        api_key = self.api_key(user)
        self.assertTrue(api_key is not None and len(api_key) > 0)
        request.META['HTTP_AUTHORIZATION'] = 'ApiKey %s:%s' % (user.username, api_key)
        auth = MicroblogApiKeyAuthentication()
        self.assertTrue(auth.is_authenticated(request))
        self.assertTrue(request.user == user)
        # unauthorized
        request.META['HTTP_AUTHORIZATION'] = 'bad authorization'
        self.assertFalse(auth.is_authenticated(request))

    def test_query_authorization(self):
        # username authorized
        request = HttpRequest()
        user = self.u2
        api_key = self.api_key(user)
        self.assertTrue(api_key is not None and len(api_key) > 0)
        request.GET['api_user'] = user.username
        request.GET['api_key'] = api_key
        auth = MicroblogApiKeyAuthentication()
        self.assertTrue(auth.is_authenticated(request))
        self.assertTrue(request.user == user)
        # email authorized
        request.GET['api_user'] = user.email
        request.GET['api_key'] = api_key
        self.assertTrue(auth.is_authenticated(request))
        self.assertTrue(request.user == user)
        # username unauthorized
        request.GET['api_user'] = 'bad_username'
        request.GET['api_key'] = api_key
        self.assertFalse(auth.is_authenticated(request))
        # email unauthorized
        request.GET['api_user'] = 'bad_email@email.com'
        request.GET['api_key'] = api_key
        self.assertFalse(auth.is_authenticated(request))
        # username and bad api key
        request.GET['api_user'] = user.username
        request.GET['api_key'] = 'bad_key'
        self.assertFalse(auth.is_authenticated(request))
        # email and bad api key
        request.GET['api_user'] = user.email
        request.GET['api_key'] = 'bad_key'
        self.assertFalse(auth.is_authenticated(request)) 

    def test_public_methods(self):
        # authorized
        request = HttpRequest()
        request.method = 'GET'
        auth = MicroblogApiKeyAuthentication(public_methods=[request.method])
        self.assertTrue(auth.is_authenticated(request))
        request = HttpRequest()

        request.method = 'POST'
        auth = MicroblogApiKeyAuthentication(public_methods=[request.method])
        self.assertTrue(auth.is_authenticated(request))

        request.method = 'PUT'
        auth = MicroblogApiKeyAuthentication(public_methods=[request.method])
        self.assertTrue(auth.is_authenticated(request))

        request.method = 'PATCH'
        auth = MicroblogApiKeyAuthentication(public_methods=[request.method])
        self.assertTrue(auth.is_authenticated(request))

        request.method = '\DELETE'
        auth = MicroblogApiKeyAuthentication(public_methods=[request.method])
        self.assertTrue(auth.is_authenticated(request))

        request.method = 'POST'
        auth = MicroblogApiKeyAuthentication(public_methods=['POST', 'GET'])
        self.assertTrue(auth.is_authenticated(request))

        # unauthorized
        request.method = 'PUT'
        self.assertFalse(auth.is_authenticated(request))

        request.method = 'PATCH'
        self.assertFalse(auth.is_authenticated(request))

        request.method = '\DELETE'
        self.assertFalse(auth.is_authenticated(request))

    def test_custom_user_identifier(self):
        # username authorized
        request = HttpRequest()
        user = self.u2
        api_key = self.api_key(user)
        self.assertTrue(api_key is not None and len(api_key) > 0)
        user_identifier = 'my_custom_user_identifier'
        auth = MicroblogApiKeyAuthentication(user_identifier=user_identifier)
        request.GET[user_identifier] = user.username
        request.GET['api_key'] = api_key
        self.assertTrue(auth.is_authenticated(request))
        self.assertTrue(request.user == user)
        # email authorized
        request.GET[user_identifier] = user.username
        request.GET['api_key'] = api_key
        self.assertTrue(auth.is_authenticated(request))
        self.assertTrue(request.user == user)
        # username unauthorized
        request.GET[user_identifier] = 'bad_username'
        request.GET['api_key'] = api_key
        self.assertFalse(auth.is_authenticated(request))
        # email unauthorized
        request.GET[user_identifier] = 'bad_email@email.com'
        request.GET['api_key'] = api_key
        self.assertFalse(auth.is_authenticated(request))
        # username and bad api key
        request.GET[user_identifier] = user.username
        request.GET['api_key'] = 'bad_key'
        self.assertFalse(auth.is_authenticated(request))
        # email and bad api key
        request.GET[user_identifier] = user.email
        request.GET['api_key'] = 'bad_key'
        self.assertFalse(auth.is_authenticated(request))
        