from django.conf.urls import *
from tastypie.resources import ModelResource
from tastypie import fields
from tastypie.authorization import Authorization
from tastypie.utils import trailing_slash
from microblog_app.models import Post, User


class UserResource(ModelResource):

	class Meta:
		queryset = User.objects.all()
		resource_name = 'user'
		fields = ['username', 'first_name', 'last_name']

	def override_urls(self): # prepend_urls in 0.9.12
		return [
			url(r'^(?P<resource_name>%s)/(?P<pk>\w[\w/-]*)/child%s$' % (
				self._meta.resource_name, trailing_slash()),
				self.wrap_view('dispatch_child'),
				name='api_parent_child'),
		]

	def dispatch_child(self, request, **kwargs):
		return PostResource().dispatch('list', request, **kwargs)


class PostResource(ModelResource):
	user = fields.ForeignKey(UserResource, 'user')

	class Meta:
		queryset = Post.objects.all()
		resource_name = 'post'
		authorization = Authorization()
