from django.db import models
from django.contrib import auth
from django.core.exceptions import ValidationError
from django.utils.timezone import now
from django.core.mail import send_mail
from tastypie.models import create_api_key
from uuidfield import UUIDField


class User(auth.models.User):

    follows = models.ManyToManyField('User', through='Follow', blank=True, symmetrical=False, related_name="followers")
    likes = models.ManyToManyField('Post', through='Like', blank=True, related_name="liked_by")
    shares = models.ManyToManyField('Post', through='Share', blank=True, related_name="shared_by")

    avatar_url = models.URLField(blank=True)
    
    def following_count(self):
        return self.follows.count()

    def followers_count(self):
        return self.followers.count()

    def posts_count(self):
        return self.posts.count()

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
    user = models.ForeignKey(User, related_name='posts')
    in_reply_to = models.ForeignKey('Post', related_name='replies', blank=True, null=True)
    text = models.CharField(max_length=200, db_index=True)
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

    follower = models.ForeignKey(User, related_name='follows_follower')
    followee = models.ForeignKey(User, related_name='follows_followee')
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
    post = models.ForeignKey(Post, related_name='likes')
    created_date = models.DateTimeField("date created", auto_now_add=True)

    def __unicode__(self):
        return str(self.user) + ' likes ' + str(self.post)


class Share(models.Model):

    class Meta:
        unique_together = ("user", "post")

    user = models.ForeignKey(User)
    post = models.ForeignKey(Post, related_name='shares')
    created_date = models.DateTimeField("date created", auto_now_add=True)

    def __unicode__(self):
        return str(self.user) + ' shares ' + str(self.post)

class LostPassword(models.Model):
    """
    Encapsulates the unique identifiers generated to reset passwords of users
    in the system.
    """
    email = models.EmailField(null=True, unique=True)
    uuid = UUIDField(auto=True)
    new_password = models.CharField(max_length=128, blank=True)
    created = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        user = User.objects.get(email=self.email)
        if not self.new_password:
            # Delete any previous instances for the same email and save the new one
            LostPassword.objects.filter(email=self.email).delete()
            super(LostPassword, self).save(*args, **kwargs)
            # Send mail
            # TODO: correct password reset link and use uuid instead of pk
            link = 'http://localhost:5000/resetpassword/?uuid=%s' % self.uuid
            send_mail(
                'Reset password',
                'Click the following link to reset your password\n\n%s' % link,
                'irodrigo17@gmail.com',
                [self.email],
                fail_silently=False)
        else:
            # Do password reset of the user and delete the LostPassword object
            user.set_password(self.new_password)
            user.save()
            LostPassword.objects.filter(email=self.email).delete()

    def __unicode__(self):
        return self.email

