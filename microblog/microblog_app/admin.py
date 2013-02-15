from django.contrib import admin
from microblog_app.models import Post, User, Follow, Like, Share

admin.site.register(User)
admin.site.register(Post)
admin.site.register(Follow)
admin.site.register(Like)
admin.site.register(Share)