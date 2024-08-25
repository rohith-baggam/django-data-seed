from django.conf import settings
import jwt
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser


def get_project_name():
    # ? Extract project name from ROOT_URLCONF
    urlconf = settings.ROOT_URLCONF
    project_name = urlconf.split('.')[0]
    return project_name


def token_decoder(token):
    return jwt.decode(token, settings.SECRET_KEY, algorithms="HS256")


def get_user(user_id):
    try:
        return get_user_model().objects.get(id=user_id)
    except get_user_model().DoesNotExist:
        return AnonymousUser()
