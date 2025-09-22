from django.urls import path

from .views import member, admin

app_name = 'jcr'
urlpatterns = [
    path('view/', member.view, name='view'),
    path('select/', member.select, name='select'),

    # admin
    path('manage/list/', admin.list, name='admin-list'),
    path('manage/details/', admin.details, name='admin-details'),
    path('manage/<int:round_id>/summary', admin.summary, name='admin-summary'),
    path('manage/<int:round_id>/status/set', admin.set_status, name='admin-status-set'),
    path('manage/<int:round_id>/transfer/bill', admin.transfer_bill, name='admin-transfer-bill'),
]
