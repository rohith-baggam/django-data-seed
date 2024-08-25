from django.apps import apps
from .fields import ModelFieldCharaterstics
from .utils import SUPPORTED_DJANGO_MODEL_FIELDS
from django.db import models, transaction
from ...utils.colorama_theme import StdoutTextTheme
import sys
from django_data_seed.utils.app_utils import get_filtered_models


class SeedData(ModelFieldCharaterstics, StdoutTextTheme):
    def get_models(self, app_name: str, model_name: str) -> list:
        """
        Returns a list of models in a Django project. 
        If an `app_name` is provided, it returns models for that specific app.
        If a `model_name` is provided, it filters models by that name.

        Args:
            - app_name: The name of the app to filter models by.
            - model_name: The name of the model to filter by.

        Returns:
            - A list of models.
        """
        if app_name and model_name:
            self.stdout_error("Either enter app_name or model_name")
            # sys.exit(0)

        models = get_filtered_models(
            specific_app_name=app_name,
            model_name=model_name
        )
        if not models:
            self.stdout_error(
                f"No Apps or no Models found,{str(app_name)}, {str(model_name)}")
            # sys.exit(0)

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
                    # sys.exit(0)
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

    def create_related_instance(self, related_model: models.Model, processed_models=None):
        """
        Info:
            If the model contains chain or nested relational fields, this function recursively processes these fields 
            to retrieve child instances. Otherwise, it returns a new value.

        Args:
            - related_model: The Django model class.
            - processed_models: A set to track already processed models.

        Returns:
            - A new model instance.
        """

        if processed_models is None:
            processed_models = set()

        # Avoid infinite recursion by checking if the model is already processed
        if related_model in processed_models:
            return None

        # Mark the current model as processed
        processed_models.add(related_model)

        related_fields = related_model._meta.get_fields()
        related_field_values = {}

        for field in related_fields:
            if isinstance(field, (models.AutoField, models.BigAutoField, models.SmallAutoField)):
                # Skip AutoField, handled by the database
                continue

            if isinstance(field, (models.ForeignKey, models.OneToOneField)):
                # Avoid recursion on self-related fields
                if field.related_model == related_model:
                    continue

                # If relation fields contain chain or nested relational fields,
                # this function calls itself recursively to get child instances
                related_field_values[field.name] = self.validate_and_create_related_instance(
                    field
                )
            else:
                self.validate_and_give_value(
                    field,
                    related_model,
                    related_field_values
                )

        return related_model.objects.create(**related_field_values)

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

    def SeedData(self, number_of_objects, app_name, model_name):
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
                ) for model in self.get_models(app_name, model_name) for _ in range(
                    number_of_objects
                )
            ]
