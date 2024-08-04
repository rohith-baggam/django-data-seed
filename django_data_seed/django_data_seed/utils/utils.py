from django.conf import settings


def get_project_name():
    # ? Extract project name from ROOT_URLCONF
    urlconf = settings.ROOT_URLCONF
    project_name = urlconf.split('.')[0]
    return project_name
