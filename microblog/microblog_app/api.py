from tastypie.resources import ModelResource
from microblog_app.models import Post
from django.contrib.auth.models import User

class PostResource(ModelResource):
	class Meta:
		queryset = Post.objects.all()
		resource_name = 'post'

class UserResource(ModelResource):
	class Meta:
		queryset = User.objects.all()
		resource_name = 'user'