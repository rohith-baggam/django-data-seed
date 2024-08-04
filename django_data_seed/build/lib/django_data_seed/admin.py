from django.contrib import admin
from . import models
from django_data_seed.utils.colorama_theme import StdoutTextTheme
from django_data_seed.utils.admin_utils import (
    backup_loaddata,
    load_log_entry_data
)

theme = StdoutTextTheme()


class DataBackUpModelAdmin(admin.ModelAdmin):
    list_display = ('pk', 'object_id', 'model_name')
    search_fields = ('pk', 'object_id', 'model_name')
    list_filter = ('deleted_by', 'created_at')
    actions = [backup_loaddata]


class DjangoSeedDataLogEntryModelAdmin(admin.ModelAdmin):
    list_display = ('pk', 'object_id', 'model_name')
    search_fields = ('pk', 'object_id', 'model_name')
    list_filter = ('mutated_by', 'created_at')
    actions = [load_log_entry_data]


admin.site.register(
    models.DjangoSeedDataBackUpModel,
    DataBackUpModelAdmin
)
admin.site.register(
    models.DjangoSeedDataLogEntryModel, DjangoSeedDataLogEntryModelAdmin
)
