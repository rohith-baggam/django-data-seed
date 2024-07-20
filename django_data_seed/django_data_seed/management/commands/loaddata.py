from django.apps import apps
from .fields import ModelFieldCharaterstics
from .utils import SUPPORTED_DJANGO_MODEL_FIELDS
from django.db import models, transaction
from .colorama_theme import StdoutTextTheme
import sys


class SeedData(ModelFieldCharaterstics, StdoutTextTheme):
    def get_models(self, app_name: str) -> list:
        """
        Info:
            This function returns a list of models in a Django project. If an `app_name` is provided, it will return 
            the models for that specific app.

        Args:
            - app_name: The name of the app to filter models by.

        Returns:
            - A list of models.
        """

        self.stdout_error(str(app_name))
        installed_apps = [
            app_config.name for app_config in apps.get_app_configs()
            if not app_name or app_config.name == app_name
        ]

        models = []
        for model in apps.get_models():
            if model._meta.app_label in installed_apps:
                models.append(model)
        if not models:
            self.stdout_error("No Apps or no Models found")
            sys.exit(0)
        return models

    def validate_and_give_value(
        self,
        field: object,
        model: models.Model,
        field_values: dict
    ) -> dict:
        """
            Info:
                This function generates a random value for the specified model field and adds it to the provided dictionary.

            Args:
                - field: The model field.
                - model: The Django model class.
                - field_values: The dictionary to which the generated value will be appended.

            Returns:
                - dict
        """

        for model_field in SUPPORTED_DJANGO_MODEL_FIELDS:
            if hasattr(self, model_field):
                method = getattr(self, model_field)
                try:
                    if callable(method) and isinstance(field, getattr(models, model_field)):
                        field_value = method(field, model)
                        field_values[field.name] = field_value
                        return field_values
                except Exception as e:
                    self.stdout_warning(
                        f'WARNING : Error occur while generating data for {field.name}, {str(model)}. Error : {str(e)}'
                    )

    def fill_data_to_model(self, model: models.Model) -> object:
        """
        Info:
            This function creates a new instance of the specified model.

        Args:
            - model: The Django model class.

        Returns:
            - A new instance of the specified model.
        """

        fields = model._meta.get_fields()
        field_values = {}
        many_to_many_data_instance = {}
        for field in fields:
            try:
                if isinstance(field, models.AutoField):
                    # ? Skip AutoField, handled by the database
                    continue

                if isinstance(field, (models.ForeignKey, models.OneToOneField)):
                    # ? create new related model instance
                    field_values[field.name] = self.validate_and_create_related_instance(
                        field)

                elif isinstance(field, models.ManyToManyField):
                    # ? store many to many object and append for create method
                    many_to_many_data_instance[field.name] = self.validate_and_create_related_instance(
                        field)

                else:
                    self.validate_and_give_value(field, model, field_values)

            except Exception as e:
                if not field.blank or not field.null:
                    self.stdout_error(
                        f'Error : Error occur while generating data for {field.name}, {str(model)}. Error : {str(e)}'
                    )
                    sys.exit(0)
        created_instance = model.objects.create(**field_values)
        # ? add instance created for many to many fields
        [
            getattr(
                created_instance, key
            ).add(
                many_to_many_data_instance[key]
            )
            for key in many_to_many_data_instance.keys()
        ]

        created_instance.save()
        self.stdout_info(
            f'Sucessfully populated Data for {str(model)}'
        )
        return created_instance

    def validate_and_create_related_instance(self, field: object):
        related_model = field.related_model
        return self.create_related_instance(
            related_model
        )

    def create_related_instance(self, related_model: models.Model):
        """
            Info:
                If the model contains chain or nested relational fields, this function recursively processes these fields 
                to retrieve child instances. Otherwise, it returns a new value.

            Args:
                - model: The Django model class.

            Returns:
                - A new model instance.
        """

        related_fields = related_model._meta.get_fields()
        related_field_values = {}

        for field in related_fields:
            if (
                isinstance(field, models.AutoField)
                or
                isinstance(field, models.BigAutoField)
                or
                isinstance(field, models.SmallAutoField)
            ):
                # ? Skip AutoField, handled by the database
                continue

            if isinstance(field, (models.ForeignKey, models.OneToOneField)):
                # ? if relation fields contains chain or nested relational fields this function calls itself recursively to get child instances
                related_field_values[field.name] = self.validate_and_create_related_instance(
                    field)
            else:
                self.validate_and_give_value(
                    field,
                    related_model,
                    related_field_values
                )

        return related_model.objects.create(
            **related_field_values
        )

    def str_to_object(self, class_name: str, import_path: str):
        class_object = getattr(
            __import__(
                import_path,
                fromlist=[
                    class_name
                ]
            ),
            class_name
        )
        return class_object

    def SeedData(self, number_of_objects, app_name):
        """
            Info:
                This function retrieves all models from each app, or from a specific app if `app_name` is provided. For each model,
                it creates the specified number of objects by iterating `number_of_objects` times.

            Args:
                - model: The Django model class.

            Returns:
                - New instances of the model.
        """

        with transaction.atomic():
            [
                self.fill_data_to_model(
                    model
                ) for model in self.get_models(app_name) for _ in range(
                    number_of_objects
                )
            ]
