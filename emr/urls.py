from django.conf.urls import url

from . import views

app_name = 'emr'

urlpatterns = [
    url(r'^$', views.utilisation_report, name='utilisation_report'),
    url(r'^api/resources/$', views.get_resource ,name = 'resources'),
    url(r'^api/status/$',views.get_status,name='status'),
    url(r'^api/resourceutilizationslots/$',views.get_resource_utilisation_slots,name='resourceutilizationslots'),
    url(r'^api/appointmenttypegroup/$',views.get_appointment_type_group, name='appointmenttypegroup')
]