from django.db import models

class Post(models.Model):
	text = models.CharField(max_length=200)
	created_at = models.DateTimeField("date created")

	def __unicode__(self):
		return self.text