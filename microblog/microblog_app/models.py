from django.db import models
from django.contrib.auth.models import User

class Post(models.Model):
	text = models.CharField(max_length=200)
	created_at = models.DateTimeField("date created")
	user = models.ForeignKey(User)

	def __unicode__(self):
		return self.text