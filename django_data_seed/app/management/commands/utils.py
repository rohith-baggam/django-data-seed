from faker import Faker
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.text import slugify
from django.db import models
import datetime
from typing import Any
fake = Faker()


class DatabaseUtils:
    def get_unique_char_data(self, model: models.Model, obj: models.CharField) -> str:
        """
            This function checks from database and generated char unique string

            Args:
                - obj : models related to CharFields
                - model : The django model class
            Returns :
                - Unique Character for the model fields 
        """
        max_chars = int(obj.max_length) // 2
        val = fake.name() if max_chars < 50 else fake.text(max_nb_chars=max_chars)
        if "id" in str(obj.name):
            val = str(val).replace(" ", "")
        filter_set = {obj.name: val}

        if model.objects.filter(**filter_set).exists():
            return self.get_unique_char_data(model=model, obj=obj)
        else:
            return val

    def get_unique_numeric_field_data(self, obj, model: models.Model) -> int:
        """
        Generates unique integer field for a model field by calculating highest value + 1.

        Args:
        - obj: The model field object.
        - model: The Django model class.

        Returns:
        - Character data for the model field.
        """
        value = model.objects.all().order_by(f"-{str(obj.name)}").first()
        return value + 1

    def get_min_max_value_of_integer_field(self, obj) -> tuple:
        min_value = 0
        max_value = 1000
        try:
            # Iterate through validators and extract MinValueValidator and MaxValueValidator values
            for validator in obj.validators:
                if isinstance(validator, MinValueValidator):
                    min_value = validator.limit_value
                elif isinstance(validator, MaxValueValidator):
                    max_value = validator.limit_value

            return (min_value, max_value)
        except Exception:
            return (min_value, max_value)

    def set_length_for_decimal(self, max_digit: int, decimal_places: int, max_length: int) -> tuple:
        if max_length >= max_digit + decimal_places:
            return (max_digit, decimal_places)
        return self.set_length_for_decimal(
            max_digit=max_length % max_digit,
            decimal_places=max_length % decimal_places,
            max_length=max_length
        )

    def get_unique_value(self, model: models.Model, obj, value) -> Any:
        value = value()
        if model.objects.filter(**{obj.name: value}).exists():
            return self.get_unique_value(model=model, obj=obj, value=value())
        else:
            return value

    def generate_random_duration(self) -> datetime.timedelta:
        # Random number of days (0 to 365)
        days = fake.random_int(min=0, max=365)
        # Random number of hours (0 to 23)
        hours = fake.random_int(min=0, max=23)
        # Random number of minutes (0 to 59)
        minutes = fake.random_int(min=0, max=59)
        # Random number of seconds (0 to 59)
        seconds = fake.random_int(min=0, max=59)

        return datetime.timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)

    def generate_numeric_value(self, obj, model):
        min_value, max_value = self.get_min_max_value_of_integer_field(obj=obj)

        if obj.unique or obj.primary_key:
            val = self.get_unique_numeric_field_data(obj=obj, model=model)
        else:
            val = fake.random_int(min=min_value, max=max_value)
        return val


SUPPORTED_DJANGO_MODEL_FIELDS = [
    "BooleanField",
    "EmailField",
    "CharField",
    "DecimalField",
    "FloatField",
    "IntegerField",
    "UUIDField",
    "PositiveBigIntegerField",
    "PositiveIntegerField",
    "PositiveSmallIntegerField",
    "SmallIntegerField",
    "BigIntegerField",
    "DateField",
    "DateTimeField",
    "TimeField",
    "TextField",
    "SlugField",
    "URLField",
    "IPAddressField",
    "GenericIPAddressField",
    "BinaryField",
    "DurationField"
]
