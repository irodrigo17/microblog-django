from django.conf.urls import *
from tastypie.resources import ModelResource
from tastypie import fields
from tastypie.authorization import Authorization
from tastypie.utils import trailing_slash
from microblog_app.models import *


class UserResource(ModelResource):
	followers = fields.IntegerField(attribute='followers_count', readonly=True)
	following = fields.IntegerField(attribute='following_count', readonly=True)

	class Meta:
		queryset = User.objects.all()
		resource_name = 'user'
		fields = ['username', 'first_name', 'last_name']
		authorization = Authorization()

class PostResource(ModelResource):
	user = fields.ForeignKey(UserResource, 'user')
	replies = fields.ToManyField('microblog_app.api.PostResource', 'replies', null=True, full=True, blank=True)
	in_reply_to = fields.ForeignKey('microblog_app.api.PostResource', 'in_reply_to', null=True, blank=True)

	likes = fields.IntegerField(attribute='liked_by_count', readonly=True)
	shares = fields.IntegerField(attribute='shared_by_count', readonly=True)

	class Meta:
		queryset = Post.objects.all()
		resource_name = 'post'
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
		authorization = Authorization()
		filtering = {
			"user": ('exact',),
			"post": ('exact',),
		}

