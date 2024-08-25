from django.contrib import admin
from . import models
from django.apps import apps
# Register your models here.
models = apps.get_app_config("sub_app_1").get_models()

[admin.site.register(model) for model in models]
