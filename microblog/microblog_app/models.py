from django.db import models
from django.contrib import auth

class User(auth.models.User):
	follows = models.ManyToManyField('User', related_name='followed_by', blank=True, symmetrical=False)
	likes = models.ManyToManyField('Post', related_name='liked_by', blank=True)
	shares = models.ManyToManyField('Post', related_name='shared_by', blank=True)

	def following_count(self):
		return self.following.count()

	def followers_count(self):
		return self.following_set.count()

class Post(models.Model):
	text = models.CharField(max_length=200)
	created_at = models.DateTimeField("date created")
	user = models.ForeignKey(User)
	in_reply_to = models.ForeignKey('Post', related_name='replies', blank=True, null=True)

	def __unicode__(self):
		return self.text

