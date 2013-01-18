from django.db import models
from django.contrib import auth
from tastypie.models import create_api_key

class User(auth.models.User):
	follows = models.ManyToManyField('User', through='Follow', blank=True, symmetrical=False)
	likes = models.ManyToManyField('Post', through='Like', blank=True, related_name="liked_by")
	shares = models.ManyToManyField('Post', through='Share', blank=True, related_name="shared_by")

	def following_count(self):
		return self.follows.count()

	def followers_count(self):
		return self.followed_by.count()

	def full_name(self):
		return self.first_name + ' ' + self.last_name

	def __unicode__(self):
		return self.username

# Hook tastypie's create_api_key signal to the User model.
models.signals.post_save.connect(create_api_key, sender=User)


class Post(models.Model):
	user = models.ForeignKey(User)
	in_reply_to = models.ForeignKey('Post', related_name='replies', blank=True, null=True)
	text = models.CharField(max_length=200)
	created_date = models.DateTimeField("date created", auto_now_add=True)
	modified_date = models.DateTimeField("date modified", auto_now=True)	

	def liked_by_count(self):
		return self.liked_by.count()

	def shared_by_count(self):
		return self.shared_by.count()

	def replies_count(self):
		return self.replies.count()

	def __unicode__(self):
		return self.text


class Follow(models.Model):
	follower = models.ForeignKey(User, related_name='following')
	followee = models.ForeignKey(User, related_name='followed_by')
	created_date = models.DateTimeField(blank=True, auto_now_add=True)

	def __unicode__(self):
		return str(self.follower) + ' follows ' + str(self.followee)


class Like(models.Model):
	user = models.ForeignKey(User)
	post = models.ForeignKey(Post)
	created_date = models.DateTimeField("date created", auto_now_add=True)

	def __unicode__(self):
		return str(self.user) + ' likes ' + str(self.post)


class Share(models.Model):
	user = models.ForeignKey(User)
	post = models.ForeignKey(Post)
	created_date = models.DateTimeField("date created", auto_now_add=True)

	def __unicode__(self):
		return str(self.user) + ' shares ' + str(self.post)

