from django.db import models
from django.contrib import auth
from django.core.exceptions import ValidationError
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

	# Overriding to add check for min password length.
	# TODO: check if this can be done in a more elegant way (by adding a MinLengthValidator to the password field for example).
	def set_password(self, raw_password):
		MIN_RAW_PASSWORD_LENGTH = 4
		if len(raw_password) < MIN_RAW_PASSWORD_LENGTH:
			raise ValidationError(u'Password is too short, at least %d characters required.' % MIN_RAW_PASSWORD_LENGTH)
		super(User, self).set_password(raw_password)

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

	class Meta:
		unique_together = ("follower", "followee")		

	follower = models.ForeignKey(User, related_name='following')
	followee = models.ForeignKey(User, related_name='followed_by')
	created_date = models.DateTimeField(blank=True, auto_now_add=True)

	def __unicode__(self):
		return str(self.follower) + ' follows ' + str(self.followee)

	# Overriding save to enforce a non erflexive relation.
	# TODO: investigate the bulk update case that this may be missing.
	def save(self, *args, **kwargs):
		# Validate non-reflexive relation.
		if self.followee == self.follower:
			raise ValidationError("Can't follow yourself")
		# Call actual save.
		super(Follow, self).save(*args, **kwargs)

class Like(models.Model):

	class Meta:
		unique_together = ("user", "post")

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

