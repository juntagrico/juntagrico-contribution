from django.urls import path
from .views import member, admin

app_name = 'jcr'
urlpatterns = [
    path('view/', member.view, name='view'),
    path('select/', member.select, name='select'),

    # admin
    path('manage/list/', admin.list, name='admin-list'),
    path('manage/summary/<int:round_id>', admin.summary, name='admin-summary'),
]
