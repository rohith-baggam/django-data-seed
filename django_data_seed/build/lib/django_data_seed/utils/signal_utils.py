from django.core.serializers import serialize
import json
from .get_user import get_current_user
from typing import Type
from django.db import models
from django_data_seed.utils.colorama_theme import StdoutTextTheme
from django.db.models.query import QuerySet
from django_data_seed.utils.json_compare import compare_json_objects
from django_data_seed.utils.thread_locals import (
    get_thread_variable
)

colorma_theme = StdoutTextTheme()


def serialize_signal_data(sender: Type[models.Model], instance: models.Model) -> dict:
    """
        Args:
            sender: The model class sending the signal.
            instance: The instance of the model being sent in the signal.

        Info:
            This function takes signal arguments and returns the data in a serialized dictionary format.

        Returns:
            A dictionary representation of the model instance.
    """
    # ? Serialize the instance data
    serialized_data = serialize('json', [instance])
    parsed_data = json.loads(serialized_data)[0]
    fields_data = parsed_data['fields']
    app_name = sender._meta.app_label
    model_name = sender.__name__.lower()
    data_dict = {
        "pk": str(instance.pk),
        "model": f"{app_name}.{model_name}",
        "fields": fields_data
    }
    return data_dict


def data_backup_pre_save_handler(
        sender: Type[models.Model],
        instance: models.Model
):
    """
        Args:
            sender: The model class sending the signal.
            instance: The instance of the model being sent in the signal.

        Info:
            This function takes the signal arguments and returns the data in a serialized dictionary format, including the model's information before any mutations.

        Returns:
            A dictionary representation of the model instance data for DjangoSeedDataLogEntryModel.
    """
    # ? Prepare data dictionary to load
    data_dict = {
        'data': serialize_signal_data(
            sender=sender,
            instance=instance
        ),
        'object_id': instance.pk,
        'model_name': sender.__name__,
    }
    # ? Add the user who deleted the object
    login_user = get_current_user()
    if login_user:
        data_dict['deleted_by'] = login_user
    return data_dict


def data_logentry_prev_save_handler(
    sender: Type[models.Model],
    instance: models.Model
) -> dict:
    """
        Args:
            sender: The model class sending the signal.
            instance: The instance of the model being sent in the signal.

        Info:
            This function takes the signal arguments and returns the data in a serialized dictionary format, including the model's information before any data in the object is mutated.

        Returns:
            A dictionary representation of the model instance data for DjangoSeedDataLogEntryModel.
    """
    # ? Prepare data dictionary to load
    instance = sender.objects.get(pk=instance.pk)
    data_dict = {
        'before_mutation': serialize_signal_data(
            sender=sender,
            instance=instance
        ),
        'object_id': instance.pk,
        'model_name': sender.__name__,
    }
    # ? Add the user who deleted the object
    login_user = get_current_user()
    if login_user:
        data_dict['mutated_by'] = login_user
    return data_dict


def data_logentry_post_save_handler(
    sender: Type[models.Model],
    instance: models.Model,
    queryset: QuerySet[models.Model]
) -> bool:
    """
        Args:
            sender: The model class that sent the signal.
            instance: The instance of the model being processed.
            queryset: The queryset of the model.

        Description:
            This function handles the post-save signal to create a new log entry if any changes were made
            to the model instance. It checks for changes and records them to ensure that modifications
            are properly logged.

        Returns:
            bool: Returns `True` if a log entry was successfully created for the changes in the instance;
                otherwise, returns `False`.
    """

    # ? Prepare data dictionary to load
    data_dict = {
        'after_mutation': serialize_signal_data(
            sender=sender,
            instance=instance
        )
    }
    pk = get_thread_variable(
        name="django_data_seed_auto_logentry_pk",
    )
    if not pk:
        return False
    try:
        instance = queryset.get(pk=pk)
    except sender.DoesNotExist:
        return False
    is_changes_exists = compare_json_objects(
        obj1=instance.before_mutation,
        obj2=data_dict['after_mutation']
    )
    # ? only update if any changes happend
    if not is_changes_exists:
        # ? update new mutated data to logentry
        queryset.filter(
            pk=pk).update(**data_dict)
    else:
        instance.delete()
        return True
