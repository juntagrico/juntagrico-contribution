"""
test URL Configuration for juntagrico_contribution development
"""
from django.urls import include, path
from django.contrib import admin

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('juntagrico.urls')),
    path('jcr/', include('juntagrico_contribution.urls')),
    path('impersonate/', include('impersonate.urls')),
]
