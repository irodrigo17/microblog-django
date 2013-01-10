from django.conf.urls import *
from microblog_app.api import PostResource, UserResource


from django.contrib import admin
admin.autodiscover()

post_resource = PostResource()
user_resource = UserResource()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'microblog.views.home', name='home'),
    # url(r'^microblog/', include('microblog.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    url(r'^admin/', include(admin.site.urls)),
    url(r'^api/', include(post_resource.urls)),
    url(r'^api/', include(user_resource.urls)),
)
