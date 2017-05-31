from django.contrib import admin

from .models import Status
from .models import StatusGroup
from .models import Resource
from .models import ResourceGroup


class AdminStatus(admin.ModelAdmin):

    def has_add_permission(self, request):
        return

class AdminResource(admin.ModelAdmin):

    def has_add_permission(self, request):
        return

admin.site.register(Status, AdminStatus)
admin.site.register(StatusGroup)
admin.site.register(Resource, AdminResource)
admin.site.register(ResourceGroup)

