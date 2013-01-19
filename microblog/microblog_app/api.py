from django.conf.urls import *
from tastypie.resources import *
from tastypie import fields
from tastypie.authentication import *
from tastypie.authorization import *
from tastypie.utils import trailing_slash
from microblog_app.models import *


class UserResource(ModelResource):
	followers = fields.IntegerField(attribute='followers_count', readonly=True)
	following = fields.IntegerField(attribute='following_count', readonly=True)

	class Meta:
		queryset = User.objects.all()
		resource_name = 'user'
		fields = ['username', 'first_name', 'last_name', 'email', 'id']
		authentication = Authentication()
		authorization = Authorization()

	# Overriding this method to set password properly using set_password
	def obj_create(self, bundle, request=None, **kwargs):
		bundle = super(UserResource, self).obj_create(bundle, request, **kwargs)
		bundle.obj.set_password(bundle.data.get('password'))
		bundle.obj.save() 
		return bundle

class PostResource(ModelResource):
	user = fields.ForeignKey(UserResource, 'user')
	in_reply_to = fields.ForeignKey('microblog_app.api.PostResource', 'in_reply_to', null=True, blank=True)

	likes = fields.IntegerField(attribute='liked_by_count', readonly=True)
	shares = fields.IntegerField(attribute='shared_by_count', readonly=True)
	replies = fields.IntegerField(attribute='replies_count', readonly=True)

	class Meta:
		queryset = Post.objects.all()
		resource_name = 'post'
		authentication = Authentication()
		authorization = Authorization()
		filtering = {
			"user": ('exact',),
		}

class FollowResource(ModelResource):
	follower = fields.ForeignKey(UserResource, 'follower')
	followee = fields.ForeignKey(UserResource, 'followee')

	class Meta:
		queryset = Follow.objects.all()
		resource_name = 'follow'
		# authentication = ApiKeyAuthentication()
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
		authentication = Authentication()
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
		authentication = Authentication()
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
        if not 'email' in data:
            errors.append('You must provide an "email" field.')
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

        email = deserialized['email']
        password = deserialized['password']

        try:
            user = User.objects.get(email=email)
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
