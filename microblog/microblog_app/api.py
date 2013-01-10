from tastypie.resources import ModelResource
from microblog_app.models import Post
from django.contrib.auth.models import User
from tastypie import fields
from tastypie.authorization import Authorization

class UserResource(ModelResource):
	class Meta:
		queryset = User.objects.all()
		resource_name = 'user'
		fields = ['username', 'first_name', 'last_name', 'last_login']

class PostResource(ModelResource):
	user = fields.ForeignKey(UserResource, 'user')

	class Meta:
		queryset = Post.objects.all()
		resource_name = 'post'
		authorization = Authorization()
