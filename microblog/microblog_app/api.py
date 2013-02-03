from django.conf.urls import url
from django.db import IntegrityError, transaction
from django.db.models import Q, Count, Sum
from tastypie.resources import ModelResource, Resource
from tastypie import fields
from tastypie.authentication import ApiKeyAuthentication
from tastypie.authorization import Authorization
from tastypie.utils import trailing_slash
from tastypie.paginator import Paginator
from haystack.query import SearchQuerySet, EmptySearchQuerySet
from microblog_app.models import *
import microblog_app
import logging
import operator


# Get an instance of a logger
logger = logging.getLogger(__name__)


# TODO: Add authorization.

# ApiKeyAuthentication with 'free' (unauthenticated) POST.
class FreePostApiKeyAuthentication(ApiKeyAuthentication):

	def is_authenticated(self, request, **kwargs):
		return (request.method in ['POST', 'GET']) or super(FreePostApiKeyAuthentication, self).is_authenticated(request, **kwargs)

	# Optional but recommended
	def get_identifier(self, request):
		return request.user.username


# TODO: Get haystack search working properly and compare with custom search.
class HaystackSearchableModelResource(ModelResource):
	"""
	Base class for all searchable resources. It creates a custom endpoit at /<resource_name>/search/ 
	and expects the query string to contain a 'q' parameter with the search query.

	It uses Haystack for searching by default, but subclasses can also override get_search to provide custom search.
	If Haystack is used, then subclasses need to override get_model and return the proper django model class.
	Defualt Haystack search also paginates the results, tastypie style.
	"""

	def override_urls(self):
		return [
			url(r"^(?P<resource_name>%s)/search%s$" % (self._meta.resource_name, trailing_slash()), self.wrap_view('get_search'), name="api_get_search"),
		]

	def get_search(self, request, **kwargs):
		self.method_check(request, allowed=['get'])
		self.is_authenticated(request)
		self.throttle_check(request)

		# Do the query.
		sqs = SearchQuerySet().models(self.get_model()).load_all().auto_query(request.GET.get('q', ''))

		# Paginate the results.
		paginator = self._meta.paginator_class(request.GET, sqs, resource_uri=self.get_resource_list_uri(), limit=self._meta.limit)
		logger.debug('Paginator ready')

		# Create response
		bundles = []
		objects = paginator.page()['objects']
		logger.debug('objects: '+str(objects))
		for result in objects:			
			logger.debug('result: '+str(result))
			bundle = self.build_bundle(obj=result.object, request=request)
			logger.debug('bundle: '+str(bundle))
			bundles.append(self.full_dehydrate(bundle))
			logger.debug('dehydrated bundles: '+str(bundles))
		 
		object_list = {
			'meta': paginator.page()['meta'],
			'objects': bundles
		}

		self.log_throttled_access(request)
		return self.create_response(request, object_list)

	def get_model(self):
		raise RuntimeError('Override me')


# TODO: refine this class
class SearchableModelResource(ModelResource):

	def override_urls(self):
		return [
			url(r"^(?P<resource_name>%s)/search%s$" % (self._meta.resource_name, trailing_slash()), self.wrap_view('get_search'), name="api_get_search"),
		]

	# TODO: find a better way of specifying 'searchable fields'
	def get_q_objects(self, terms):
		"""
		This method shoud beoverriden by subclasses, returning an array of django.model.db.Q objects 
		that will be joined with ORs for filtering the base queryset.
		"""
		raise RuntimeError('Override me.')

	def get_terms(self, request):
		query = request.GET.get('q', '')
		return [term.strip() for term in query.split()]

	def base_query_set(self, request):
		"""
		Subclasses can override this method to provide a custom base (initial) query set.
		"""
		return self.get_object_list(request)

	def search(self, request):
		qs = self.base_query_set(request)
		terms = self.get_terms(request)
		if len(terms):
			q_objects = self.get_q_objects(terms)
			qs = qs.filter(reduce(operator.or_, q_objects))
		return qs

	def customize_query_set(self, query_set, request):
		"""
		Override to provide custom filtering or ordering to the query set.
		"""
		return query_set

	def get_search(self, request, **kwargs):
		self.method_check(request, allowed=['get'])
		self.is_authenticated(request)
		self.throttle_check(request)

		# Do the query.		
		results = self.search(request)

		# Customize query set.
		results = self.customize_query_set(results, request)

		# Paginate the results.
		paginator = self._meta.paginator_class(request.GET, results, resource_uri=self.get_resource_list_uri(), limit=self._meta.limit)

		# Create response
		bundles = []
		objects = paginator.page()['objects']
		for result in objects:			
			bundle = self.build_bundle(obj=result, request=request)
			bundles.append(self.full_dehydrate(bundle))
		 
		object_list = {
			'meta': paginator.page()['meta'],
			'objects': bundles
		}

		self.log_throttled_access(request)
		return self.create_response(request, object_list)


class UserResource(SearchableModelResource):
	followers = fields.IntegerField(attribute='followers_count', readonly=True)
	following = fields.IntegerField(attribute='following_count', readonly=True)
	posts_count = fields.IntegerField(attribute='posts_count', readonly=True)

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
		user = bundle.request.user
		if user is None or not isinstance(user, User) or not isinstance(bundle.obj, User):
			return False
		else:
			return Follow.objects.filter(follower=user, followee=bundle.obj).exists()

	def get_q_objects(self, terms):
		q_objects = []
		for term in terms:
			q_objects.append(Q(username__icontains=term))
			q_objects.append(Q(first_name__icontains=term))
			q_objects.append(Q(last_name__icontains=term))
		return q_objects

	def customize_query_set(self, query_set, request):
		return query_set.annotate(Count('followed_by', distinct=True)).order_by('-followed_by__count')



class PostResource(SearchableModelResource):
	user = fields.ForeignKey(UserResource, 'user')
	in_reply_to = fields.ForeignKey('microblog_app.api.PostResource', 'in_reply_to', null=True, blank=True)

	likes = fields.IntegerField(attribute='liked_by_count', readonly=True)
	shares = fields.IntegerField(attribute='shared_by_count', readonly=True)
	replies = fields.IntegerField(attribute='replies_count', readonly=True)

	liked_by_current_user = fields.BooleanField(readonly=True)
	shared_by_current_user = fields.BooleanField(readonly=True)

	class Meta:
		queryset = Post.objects.all()
		resource_name = 'post'
		authentication = ApiKeyAuthentication()
		authorization = Authorization()
		filtering = {
			"user": ('exact',),
			"in_reply_to": ('exact',),
		}

	def dehydrate_liked_by_current_user(self, bundle):
		return Like.objects.filter(user=bundle.request.user, post=bundle.obj).exists()

	def dehydrate_shared_by_current_user(self, bundle):
		return Share.objects.filter(user=bundle.request.user, post=bundle.obj).exists()

	def get_q_objects(self, terms):
		q_objects = []
		for term in terms:
			q_objects.append(Q(text__icontains=term))
		
		return q_objects

	def customize_query_set(self, query_set, request):
		return query_set.annotate(Count('likes', distinct=True)).order_by('-likes__count')


class FeedResource(SearchableModelResource):
	'''
	A list of posts made/shared by the user himself or made/shared by the users he's following, sorted by creation date.
	'''
	class Meta:
		queryset = Post.objects.all()
		resource_name = 'feed'
		authentication = ApiKeyAuthentication()
		authorization = Authorization()
		list_allowed_methods = ['get']

	def apply_authorization_limits(self, request, object_list):
		user = microblog_app.models.User.objects.get(pk=request.user.pk)
		follows = user.follows.all()
		return object_list.filter(
			Q(user=user) # Posts made by the user himself
			| Q(user__in=follows) # Or posts made by an user that the user is following			
			| Q(shares__user=user) # Or posts shared by the user himself
			| Q(shares__user__in=follows) # Or posts shared by an user that the user is following
		).order_by('created_date').distinct()

	def get_q_objects(self, terms):
		q_objects = []
		for term in terms:
			q_objects.append(Q(text__icontains=term))
		return q_objects

	def customize_query_set(self, query_set, request):
		return query_set.annotate(Count('likes', distinct=True)).order_by('-likes__count')

	def base_query_set(self, request):
		objects = self.get_object_list(request)
		return self.apply_authorization_limits(request, objects)


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
		if not 'username' in data or 'email' in data:
			errors.append('You must provide an "username" field or an "email" field.')
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

		if 'username' in deserialized:
			username = deserialized['username']
		else:
			email = deserialized['email']
		password = deserialized['password']

		try:
			if username:
				user = User.objects.get(username=username)
			else:
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
