from django.contrib import admin, messages
from django_data_seed.utils.colorama_theme import StdoutTextTheme
from typing import Any, Dict, List
from django.apps import apps
from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist


def process_entries_core(
        queryset: Any,
        data_type: str,
        should_delete: bool = True
) -> List[str]:
    """
    Core logic to reload data from a queryset into the corresponding models, handling
    ForeignKey, ManyToMany, and OneToOne relationships. Deletes the processed entries if no errors occur.

    Args:
        queryset (Any): The queryset of entries to process. Each entry should contain 'model', 'pk', 'fields', and any foreign key references.
        data_type (str): The type of data to use for processing ('data' or 'before_mutation').
        should_delete (bool): Whether to delete the queryset after processing.

    Returns:
        List[str]: A list of error messages.
    """
    errors = []
    try:
        with transaction.atomic():
            for query in queryset:
                entry = getattr(
                    query,
                    data_type
                )
                model_label = entry['model']
                pk = entry['pk']
                fields = entry['fields']
                try:
                    model = apps.get_model(model_label)
                    fields = handle_related_fields(model, fields)
                    update_or_create_instance(model, pk, fields)
                except LookupError:
                    errors.append(f'Error: Model {model_label} not found')
                except ObjectDoesNotExist as e:
                    errors.append(f'Error: {str(e)}')

        if not errors and should_delete:
            queryset.delete()

    except Exception as e:
        errors.append(str(e))

    return errors


def handle_related_fields(model, fields: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process and handle ForeignKey, ManyToMany, and OneToOne relationships in the fields.

    Args:
        model: The model class for which the fields are processed.
        fields (Dict[str, Any]): The fields to be processed.

    Returns:
        Dict[str, Any]: Updated fields with related objects processed.
    """
    updated_fields = fields.copy()
    for field_name, value in fields.items():
        field = model._meta.get_field(field_name)
        if field.is_relation:
            if field.many_to_one or field.one_to_one:
                updated_fields[field_name] = process_related_field(
                    field, value)
            elif field.many_to_many:
                updated_fields[field_name] = process_many_to_many_field(
                    field, value)
    return updated_fields


def process_related_field(field, value: Any) -> Any:
    """
    Process a ForeignKey or OneToOneField.

    Args:
        field: The model field.
        value (Any): The value for the field.

    Returns:
        Any: The processed value for the field.

    Raises:
        ObjectDoesNotExist: If the related instance does not exist.
    """
    if isinstance(value, dict) and 'pk' in value:
        related_model = field.related_model
        related_pk = value['pk']
        try:
            return related_model.objects.get(pk=related_pk)
        except related_model.DoesNotExist:
            raise ObjectDoesNotExist(
                f'Related instance of model {related_model.__name__} with pk={related_pk} does not exist.')
    elif isinstance(value, int):
        related_model = field.related_model
        try:
            return related_model.objects.get(pk=value)
        except related_model.DoesNotExist:
            raise ObjectDoesNotExist(
                f'Related instance of model {related_model.__name__} with pk={value} does not exist.')
    return value


def process_many_to_many_field(field, value: Any) -> List[Any]:
    """
    Process a ManyToManyField.

    Args:
        field: The model field.
        value (Any): The value for the field, which should be a list of related objects.

    Returns:
        List[Any]: A list of related objects.

    Raises:
        ObjectDoesNotExist: If any related instance does not exist.
    """
    related_instances = []
    if isinstance(value, list):
        related_model = field.related_model
        for related_entry in value:
            if isinstance(related_entry, dict) and 'pk' in related_entry:
                related_pk = related_entry['pk']
                try:
                    related_instance = related_model.objects.get(pk=related_pk)
                    related_instances.append(related_instance)
                except related_model.DoesNotExist:
                    raise ObjectDoesNotExist(
                        f'Related instance of model {related_model.__name__} with pk={related_pk} does not exist.')
            elif isinstance(related_entry, int):
                try:
                    related_instance = related_model.objects.get(
                        pk=related_entry)
                    related_instances.append(related_instance)
                except related_model.DoesNotExist:
                    raise ObjectDoesNotExist(
                        f'Related instance of model {related_model.__name__} with pk={related_entry} does not exist.')
    return related_instances


def update_or_create_instance(model, pk: Any, fields: Dict[str, Any]) -> None:
    """
    Update or create an instance of the model.

    Args:
        model: The model class.
        pk (Any): The primary key of the instance.
        fields (Dict[str, Any]): The fields to update or create the instance with.

    Returns:
        None
    """
    model.objects.update_or_create(
        pk=pk,
        defaults=fields
    )


theme = StdoutTextTheme()


def process_entries_with_admin(
        modeladmin: admin.ModelAdmin,
        request: Any,
        queryset: Any,
        data_type: str,
        should_delete: bool = True
) -> None:
    """
    Wrapper function to process entries and handle admin messages.

    Args:
        modeladmin (admin.ModelAdmin): The model admin instance that called this function.
        request (Any): The HTTP request object.
        queryset (Any): The queryset of entries to process.
        data_type (str): The type of data to use for processing ('data' or 'before_mutation').
        should_delete (bool): Whether to delete the queryset after processing.

    Returns:
        None
    """
    errors = process_entries_core(queryset, data_type, should_delete)

    if errors:
        theme.stdout_error(message="\n".join(errors))
        modeladmin.message_user(
            request, "\n".join(errors), level=messages.ERROR)
    else:
        theme.stdout_success(message="Successfully processed data")
        modeladmin.message_user(request, "Successfully processed data")


def restore_data(modeladmin: admin.ModelAdmin, request: Any, queryset: Any) -> None:
    """
    Action to backup data and process entries with deletion.

    Args:
        modeladmin (admin.ModelAdmin): The model admin instance that called this function.
        request (Any): The HTTP request object.
        queryset (Any): The queryset of entries to process.

    Returns:
        None
    """
    process_entries_with_admin(
        modeladmin, request, queryset, 'data', should_delete=True)


def load_log_entry_data(modeladmin: admin.ModelAdmin, request: Any, queryset: Any) -> None:
    """
    Action to load log entry data without deleting entries.

    Args:
        modeladmin (admin.ModelAdmin): The model admin instance that called this function.
        request (Any): The HTTP request object.
        queryset (Any): The queryset of entries to process.

    Returns:
        None
    """
    process_entries_with_admin(
        modeladmin, request, queryset, 'before_mutation', should_delete=False)
