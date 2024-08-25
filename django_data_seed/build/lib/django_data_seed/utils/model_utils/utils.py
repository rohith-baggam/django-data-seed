from django.db import models
from django.core.exceptions import ObjectDoesNotExist
from typing import Any
from django.db import transaction


def get_model_full_path(cls: models.Model):
    """
    Extract the full path of a Django model class from its class reference.

    Args:
        cls (type): The model class.

    Returns:
        str: The full path of the model in the format 'app_label.ModelName'.
    """
    # ? Get the module name
    module_name = cls.__module__
    # ? Get the class name
    class_name = cls.__qualname__.split('.')[-1]

    # ? The module_name is usually in the format 'app_name.models', so we extract 'app_name'
    app_label = module_name.split('.')[-2]

    # ? Return the formatted string
    return f"{app_label}.{class_name}"


def parse_value(value: Any, field) -> Any:
    """
    Parse a value based on the field type.

    Args:
        value (Any): The value to be parsed.
        field (Field): The Django model field instance.

    Returns:
        Any: The parsed value appropriate for the field type.
    """
    if field.many_to_many:
        # ? For many-to-many fields, we expect a list of primary keys
        return value
    elif field.get_internal_type() == 'ForeignKey':
        # ? For ForeignKey fields, we expect a single primary key
        return value
    return value


def load_object(model_name: str, pk: Any, data: dict):
    """
    Load a single object into the database from a serialized dictionary.

    Args:
        model_name (str): The name of the model in the format 'app_label.ModelName'.
        pk (Any): The primary key of the object to be loaded or created.
        data (dict): A dictionary containing the serialized data for the object.
    """
    try:
        # ? Split the model_name into app_label and model_name
        app_label, model_name = model_name.split('.')

        # ? Get the model class from the app and model name
        model = apps.get_model(app_label, model_name)

        # ? Extract primary key and fields from the data
        fields = {}
        many_to_many_fields = {}

        for field, value in data.get('fields', {}).items():
            field_obj = model._meta.get_field(field)
            parsed_value = parse_value(value, field_obj)

            if field_obj.many_to_many:
                many_to_many_fields[field] = parsed_value
            else:
                fields[field] = parsed_value

        # ? Check if an instance with this primary key already exists
        if pk is not None:
            try:
                instance = model.objects.get(pk=pk)
                # ? Update existing instance
                for field, value in fields.items():
                    setattr(instance, field, value)
            except ObjectDoesNotExist:
                # ? Create new instance if not found
                instance = model(**fields)
        else:
            # ? Create new instance if no primary key is provided
            instance = model(**fields)

        # ? Save the instance in a transaction to ensure atomicity
        with transaction.atomic():
            instance.save()
            # ? Handle many-to-many fields separately
            for field, values in many_to_many_fields.items():
                # ? Clear existing relationships and set new ones
                getattr(instance, field).set(values)

            instance.save()  # ? Save again after updating many-to-many fields
            print(f"Successfully loaded {model_name} with PK {pk}")

    except Exception as e:
        print(f"Error loading object: {e}")
