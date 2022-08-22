from django.contrib import admin

from .models import Volume


class VolumeAdmin(admin.ModelAdmin):
    list_display = ('pk', 'company_id', 'inn', 'volume', 'portal')
    list_filter = ('portal',)
    search_fields = ('company_id', 'inn')


admin.site.register(Volume, VolumeAdmin)
