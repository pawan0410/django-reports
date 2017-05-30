from django.contrib import admin

from .models import Status
from .models import StatusGroup


class AdminStatus(admin.ModelAdmin):

    def has_add_permission(self, request):
        return

admin.site.register(Status, AdminStatus)
admin.site.register(StatusGroup)

