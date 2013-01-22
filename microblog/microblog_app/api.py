from django.conf.urls import *
from django.db import IntegrityError
from django.db.models import Q
from tastypie.resources import *
from tastypie import fields
from tastypie.authentication import *
from tastypie.authorization import *
from tastypie.utils import trailing_slash
from microblog_app.models import *
import microblog_app
import logging


# TODO: Add authorization.

# ApiKeyAuthentication with 'free' (unauthenticated) POST.
class FreePostApiKeyAuthentication(ApiKeyAuthentication):

	def is_authenticated(self, request, **kwargs):
		return request.method == 'POST' or super(FreePostApiKeyAuthentication, self).is_authenticated(request, **kwargs)

    # Optional but recommended
	def get_identifier(self, request):
		return request.user.username


class UserResource(ModelResource):
	followers = fields.IntegerField(attribute='followers_count', readonly=True)
	following = fields.IntegerField(attribute='following_count', readonly=True)

	followed_by_current_user = fields.BooleanField(readonly=True)

	class Meta:
		queryset = User.objects.all()
		resource_name = 'user'
		fields = ['username', 'first_name', 'last_name', 'email', 'id']
		authentication = FreePostApiKeyAuthentication()
		authorization = Authorization()
		filtering = {
			"username": ('exact',), # Needed for ApiKeyAuthorization to work.
		}

	@transaction.commit_on_success # TODO: enforce this at DB level instead of API level.
	def obj_create(self, bundle, request=None, **kwargs):
		'''
		Overriding this method to set password properly using set_password
		It needs to be transactional so django.contrib.auth.models.User instances don't remain on the DB if something goes wrong.
		'''
		try:
			bundle = super(UserResource, self).obj_create(bundle, request, **kwargs)
			bundle.obj.set_password(bundle.data.get('password'))
			bundle.obj.save() 
		except IntegrityError:
			raise BadRequest('The username already exists')
		return bundle

	def dehydrate_followed_by_current_user(self, bundle):
		return Follow.objects.filter(follower=bundle.request.user, followee=bundle.obj).exists()

class PostResource(ModelResource):
	user = fields.ForeignKey(UserResource, 'user')
	in_reply_to = fields.ForeignKey('microblog_app.api.PostResource', 'in_reply_to', null=True, blank=True)

	likes = fields.IntegerField(attribute='liked_by_count', readonly=True)
	shares = fields.IntegerField(attribute='shared_by_count', readonly=True)
	replies = fields.IntegerField(attribute='replies_count', readonly=True)

	liked_by_current_user = fields.BooleanField(readonly=True)

	class Meta:
		queryset = Post.objects.all()
		resource_name = 'post'
		authentication = ApiKeyAuthentication()
		authorization = Authorization()
		filtering = {
			"user": ('exact',),
		}

	def dehydrate_liked_by_current_user(self, bundle):
		return Like.objects.filter(user=bundle.request.user, post=bundle.obj).exists()


class FeedResource(ModelResource):
	'''
	A list of posts by the user himself or the users he's following, sorted by creation date.
	'''
	class Meta:
		queryset = Post.objects.all()
		resource_name = 'feed'
		authentication = ApiKeyAuthentication()
		authorization = Authorization()
		list_allowed_methods = ['get']

	def apply_authorization_limits(self, request, object_list):
		# TODO: find a more efficient way to do it (if any), and maybe some way to get this in the model itself so it can be properly tasted.
		user = microblog_app.models.User.objects.get(pk=request.user.pk)
		filter_list = user.follows.all()
		return object_list.filter(Q(user__in=filter_list) | Q(user=user)).order_by('created_date')


class FollowResource(ModelResource):
	follower = fields.ForeignKey(UserResource, 'follower')
	followee = fields.ForeignKey(UserResource, 'followee')

	class Meta:
		queryset = Follow.objects.all()
		resource_name = 'follow'
		authentication = ApiKeyAuthentication()
		authorization = Authorization()
		filtering = {
			"follower": ('exact',),
			"followee": ('exact',),
		}

class LikeResource(ModelResource):
	user = fields.ForeignKey(UserResource, 'user')
	post = fields.ForeignKey(PostResource, 'post')

	class Meta:
		queryset = Like.objects.all()
		resource_name = 'like'
		authentication = ApiKeyAuthentication()
		authorization = Authorization()
		filtering = {
			"user": ('exact',),
			"post": ('exact',),
		}

class ShareResource(ModelResource):
	user = fields.ForeignKey(UserResource, 'user')
	post = fields.ForeignKey(PostResource, 'post')

	class Meta:
		queryset = Share.objects.all()
		resource_name = 'share'
		authentication = ApiKeyAuthentication()
		authorization = Authorization()
		filtering = {
			"user": ('exact',),
			"post": ('exact',),
		}

class LoginResource(Resource):
    """
	Used to obtain the API key assigned to a user for a period of time, using
	his email and password.
	"""

    class Meta:
        resource_name = 'login'
        list_allowed_methods = ['post']

    def override_urls(self):
        return [
            url(r"^(?P<resource_name>%s)/$" % self._meta.resource_name,
                self.wrap_view('login'), name="api_login"),
        ]

    def validate_data(self, data):
        """
		Validate that the appropriate parameters are received.
		"""
        errors = []
        if not 'username' in data:
            errors.append('You must provide an "username" field.')
        if not 'password' in data:
            errors.append('You must provide a "password" field.')
        return errors

    def login(self, request, **kwargs):
        deserialized = self.deserialize(
            request,
            request.raw_post_data,
            format=request.META.get('CONTENT_TYPE', 'application/json')
        )

        errors = self.validate_data(deserialized)
        if errors:
            return self.error_response(errors, request)

        username = deserialized['username']
        password = deserialized['password']

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return self.create_response(request, 'Invalid user.',
                                        http.HttpUnauthorized)
        if not user.is_active:
            return self.create_response(request, 'Your account is disabled.',
                                        http.HttpUnauthorized)

        if not user.check_password(password):
            return self.create_response(request, 'Incorrect password.',
                                        http.HttpUnauthorized)

        api_key = user.api_key

        user_resource = UserResource()
        response_data = {
            'api_key': api_key.key,
            'user': user_resource.get_resource_uri(user)
        }

        return self.create_response(request, response_data)
