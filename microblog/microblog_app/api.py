from django.conf.urls import url
from django.db import IntegrityError, transaction
from django.db.models import Q, Count, Sum
from django.core.validators import email_re
from django.core.exceptions import ObjectDoesNotExist
from tastypie.http import HttpUnauthorized, HttpNotFound
from tastypie.resources import ModelResource, Resource
from tastypie import fields
from tastypie.authentication import ApiKeyAuthentication
from tastypie.authorization import Authorization
from tastypie.utils import trailing_slash
from tastypie.paginator import Paginator
from tastypie.constants import ALL_WITH_RELATIONS
from haystack.query import SearchQuerySet, EmptySearchQuerySet
from microblog_app.models import *
import microblog_app
import logging
import operator


# Get an instance of a logger
logger = logging.getLogger(__name__)


# TODO: Add authorization.

class MicroblogApiKeyAuthentication(ApiKeyAuthentication):
    """
    Handles custom API Key authentication.
    - Supports HTTP header authentication, implemented in tastypie head, but not in current stable version 0.9.11.
    - Supports overriding the user identifier key for query parameter authentication, 
    which defaults to 'api_user' instead of username to avoid collision with filters.
    - Support for 'public methods' (HTTP methods which don't require authentication), defaults to [].
    - Automatic support for email and username as 'user_identifier', it first checks if the provided 
    'user_identifier' is a valid email address, if it's not it assumes it's an username. 
    """

    public_methods = []
    user_identifier = 'api_user'
    
    def __init__(self, user_identifier='api_user', public_methods=[]):
        super(MicroblogApiKeyAuthentication, self).__init__()
        self.public_methods = public_methods
        self.user_identifier = user_identifier

    def _unauthorized(self):
        return False

    def is_valid_email(self, email):
        return True if email and email_re.match(email) else False

    def extract_credentials(self, request):
        if request.META.get('HTTP_AUTHORIZATION') and request.META['HTTP_AUTHORIZATION'].lower().startswith('apikey '):
            (auth_type, data) = request.META['HTTP_AUTHORIZATION'].split()

            if auth_type.lower() != 'apikey':
                raise ValueError("Incorrect authorization header.")

            user_identifier, api_key = data.split(':', 1)
        else:
            user_identifier = request.GET.get(self.user_identifier) or request.POST.get(self.user_identifier)
            api_key = request.GET.get('api_key') or request.POST.get('api_key')

        user_identifier_type = 'email' if self.is_valid_email(user_identifier) else 'username'

        return user_identifier, api_key, user_identifier_type

    def get_key(self, user, api_key):
        """
        Attempts to find the API key for the user. Uses ``ApiKey`` by default
        but can be overridden.
        """
        from tastypie.models import ApiKey

        try:
            ApiKey.objects.get(user=user, key=api_key)
        except ApiKey.DoesNotExist:
            return self._unauthorized()

        return True
    
    def is_authenticated(self, request, **kwargs):
        """
        Finds the user and checks their API key.

        Should return either ``True`` if allowed, ``False`` if not or an
        ``HttpResponse`` if you need something custom.
        """

        # check public methods
        if request.method in self.public_methods:
            return True

        # check authorization parameters
        try:
            user_identifier, api_key, user_identifier_type = self.extract_credentials(request)
        except ValueError:
            return self._unauthorized()

        if not user_identifier or not api_key:
            return self._unauthorized()

        try:
            if user_identifier_type == 'username':
                user = User.objects.get(username=user_identifier)
            else:
                user = User.objects.get(email=user_identifier)
        except (User.DoesNotExist, User.MultipleObjectsReturned):
            return self._unauthorized()

        if not user.is_active:
            return False

        request.user = user
        return self.get_key(user, api_key)


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

        # Create response
        bundles = []
        objects = paginator.page()['objects']
        for result in objects:          
            bundle = self.build_bundle(obj=result.object, request=request)
            bundles.append(self.full_dehydrate(bundle))
         
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

    class Meta:
        authentication = MicroblogApiKeyAuthentication()

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
        # TODO: Check if possible to reuse URI form override_urls
        search_uri = '%ssearch%s' % (self.get_resource_list_uri(), trailing_slash())
        paginator = self._meta.paginator_class(request.GET, results, resource_uri=search_uri, limit=self._meta.limit)

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
    followers_count = fields.IntegerField(attribute='followers_count', readonly=True)
    following_count = fields.IntegerField(attribute='following_count', readonly=True)
    posts_count = fields.IntegerField(attribute='posts_count', readonly=True)

    followed_by_current_user = fields.BooleanField(readonly=True)

    class Meta:
        queryset = User.objects.all()
        resource_name = 'user'
        fields = ['username', 'first_name', 'last_name', 'email', 'id']
        authentication = MicroblogApiKeyAuthentication(public_methods=['POST'])
        authorization = Authorization()
        filtering = {
            "username": ('exact',),
            "email": ('exact',),
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
        return query_set.annotate(Count('followers', distinct=True)).order_by('-followers__count')

    def override_urls(self):
        return super(UserResource, self).override_urls() + [
            url(r"^(?P<resource_name>%s)/(?P<pk>\w[\w/-]*)/followers%s$" % (self._meta.resource_name, trailing_slash()), self.wrap_view('get_followers'), name="api_get_followers"),
            url(r"^(?P<resource_name>%s)/(?P<pk>\w[\w/-]*)/following%s$" % (self._meta.resource_name, trailing_slash()), self.wrap_view('get_following'), name="api_get_following"),
        ]

    def get_followers(self, request, **kwargs):
        # Do proper checks
        self.method_check(request, allowed=['get'])
        self.is_authenticated(request)
        self.throttle_check(request)
        self.log_throttled_access(request)

        # Get user
        try:
            user = self.cached_obj_get(request=request, **self.remove_api_resource_names(kwargs))
        except ObjectDoesNotExist:
            return HttpNotFound()
        # Get followers
        followers = user.followers.all()

        # Apply pagination
        followers_uri = '%sfollowers%s' % (self.get_resource_list_uri(), trailing_slash()) # TODO: check if there's a better way of getting the URL
        paginator = self._meta.paginator_class(request.GET, followers, resource_uri=followers_uri, limit=self._meta.limit)

        # Create response, tastypie style
        to_be_serialized = paginator.page()
        # Dehydrate the bundles in preparation for serialization.
        bundles = [self.build_bundle(obj=obj, request=request) for obj in to_be_serialized['objects']]
        to_be_serialized['objects'] = [self.full_dehydrate(bundle) for bundle in bundles]
        return self.create_response(request, to_be_serialized)

    # TODO: factorize duplicated code between this method and get_followers
    def get_following(self, request, **kwargs):
        # Do proper checks
        self.method_check(request, allowed=['get'])
        self.is_authenticated(request)
        self.throttle_check(request)
        self.log_throttled_access(request)

        # Get user
        try:
            user = self.cached_obj_get(request=request, **self.remove_api_resource_names(kwargs))
        except ObjectDoesNotExist:
            return HttpNotFound()
        # Get followers
        following = user.follows.all()

        # Apply pagination
        following_uri = '%sfollowing%s' % (self.get_resource_list_uri(), trailing_slash()) # TODO: check if there's a better way of getting the URL
        paginator = self._meta.paginator_class(request.GET, following, resource_uri=following_uri, limit=self._meta.limit)

        # Create response, tastypie style
        to_be_serialized = paginator.page()
        # Dehydrate the bundles in preparation for serialization.
        bundles = [self.build_bundle(obj=obj, request=request) for obj in to_be_serialized['objects']]
        to_be_serialized['objects'] = [self.full_dehydrate(bundle) for bundle in bundles]
        return self.create_response(request, to_be_serialized)


class PostResource(SearchableModelResource):
    user = fields.ForeignKey(UserResource, 'user', full=True)
    in_reply_to = fields.ForeignKey('microblog_app.api.PostResource', 'in_reply_to', null=True, blank=True)

    likes_count = fields.IntegerField(attribute='liked_by_count', readonly=True)
    shares_count = fields.IntegerField(attribute='shared_by_count', readonly=True)
    replies_count = fields.IntegerField(attribute='replies_count', readonly=True)

    liked_by_current_user = fields.BooleanField(readonly=True)
    shared_by_current_user = fields.BooleanField(readonly=True)

    class Meta:
        queryset = Post.objects.select_related('user').all()
        resource_name = 'post'
        authentication = MicroblogApiKeyAuthentication()
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


# TODO: factorize duplicated code between FeedResource and PostResource
class FeedResource(SearchableModelResource):
    '''
    A list of posts made/shared by the user himself or made/shared by the users he's following, sorted by creation date.
    '''
    user = fields.ForeignKey(UserResource, 'user', full=True)
    in_reply_to = fields.ForeignKey('microblog_app.api.PostResource', 'in_reply_to', null=True, blank=True)

    likes_count = fields.IntegerField(attribute='liked_by_count', readonly=True)
    shares_count = fields.IntegerField(attribute='shared_by_count', readonly=True)
    replies_count = fields.IntegerField(attribute='replies_count', readonly=True)

    liked_by_current_user = fields.BooleanField(readonly=True)
    shared_by_current_user = fields.BooleanField(readonly=True)

    class Meta:
        queryset = Post.objects.select_related('user').all()
        resource_name = 'feed'
        authentication = MicroblogApiKeyAuthentication()
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

    def dehydrate_liked_by_current_user(self, bundle):
        return Like.objects.filter(user=bundle.request.user, post=bundle.obj).exists()

    def dehydrate_shared_by_current_user(self, bundle):
        return Share.objects.filter(user=bundle.request.user, post=bundle.obj).exists()


class FollowResource(ModelResource):
    follower = fields.ForeignKey(UserResource, 'follower')
    followee = fields.ForeignKey(UserResource, 'followee')

    class Meta:
        queryset = Follow.objects.all()
        resource_name = 'follow'
        authentication = MicroblogApiKeyAuthentication()
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
        authentication = MicroblogApiKeyAuthentication()
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
        authentication = MicroblogApiKeyAuthentication()
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
