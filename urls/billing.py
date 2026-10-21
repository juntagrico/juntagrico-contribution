from django.urls import path, include


urlpatterns = [
    path('', include('urls.dev')),
    path('jb/', include('juntagrico_billing.urls')),
]
