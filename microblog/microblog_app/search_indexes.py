from django.utils.timezone import now
from haystack.indexes import *
from haystack import site
from microblog_app.models import Post, User


class PostIndex(SearchIndex):
    text = CharField(document=True, use_template=True)

    def get_model(self):
        return Post

    def index_queryset(self, using=None):
        """Used when the entire index for model is updated."""
        return self.get_model().objects.filter(created_date__lte=now())

site.register(Post, PostIndex)


class UserIndex(SearchIndex):
    text = CharField(document=True, use_template=True)

    def get_model(self):
        return User

    def index_queryset(self, using=None):
        """Used when the entire index for model is updated."""
        return self.get_model().objects.filter(date_joined__lte=now())

site.register(User, UserIndex)
