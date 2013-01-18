from django.contrib import admin
from microblog_app.models import Post, User, Follow, Like, Share
from tastypie.models import ApiKey, ApiAccess

admin.site.register(Post)
admin.site.register(User)
admin.site.register(Follow)
admin.site.register(Like)
admin.site.register(Share)
admin.site.register(ApiKey)
admin.site.register(ApiAccess)