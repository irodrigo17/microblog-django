from django.conf.urls import *
from tastypie.api import Api
from microblog_app.api import *
from django.contrib import admin

# Init admin
admin.autodiscover()

# Init tastypie
v1_api = Api(api_name='v1')
v1_api.register(UserResource())
v1_api.register(PostResource())
v1_api.register(FollowResource())
v1_api.register(LikeResource())
v1_api.register(ShareResource())
v1_api.register(LoginResource())

# define URL patterns
urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'microblog.views.home', name='home'),
    # url(r'^microblog/', include('microblog.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    url(r'^admin/', include(admin.site.urls)),
    url(r'^api/', include(v1_api.urls)),
)
