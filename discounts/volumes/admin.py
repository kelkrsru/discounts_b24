from django.contrib import admin
from .models import Volume


class VolumeAdmin(admin.ModelAdmin):
    list_display = ('pk', 'nomenclature_group_id', 'company_id', 'volume',
                    'portal')
    list_filter = ('portal', 'nomenclature_group_id',)
    search_fields = ('company_id',)


admin.site.register(Volume, VolumeAdmin)
