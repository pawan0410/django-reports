from django.contrib import admin

from .models import Status
from .models import StatusGroup
from .models import Resource
from .models import ResourceGroup
from .models import AppointmentType
from .models import AppointmentTypeGroup
from .models import ResourceUtilizationSlots


class AdminStatus(admin.ModelAdmin):

    def has_add_permission(self, request):
        return


class AdminResource(admin.ModelAdmin):
    def has_add_permission(self, request):
        return


class AdminAppointmentType(admin.ModelAdmin):
    def has_add_permission(self, request):
        return


class AdminResourceUtilizationSlots(admin.ModelAdmin):
    list_display = ('resource_id', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday')

admin.site.register(Status, AdminStatus)
admin.site.register(StatusGroup)
admin.site.register(Resource, AdminResource)
admin.site.register(ResourceGroup)
admin.site.register(AppointmentType, AdminAppointmentType)
admin.site.register(AppointmentTypeGroup)

admin.site.register(ResourceUtilizationSlots, AdminResourceUtilizationSlots)

