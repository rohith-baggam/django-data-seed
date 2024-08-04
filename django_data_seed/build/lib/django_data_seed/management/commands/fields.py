from ...utils.colorama_theme import StdoutTextTheme
from django.db import models
from faker import Faker
from .utils import DatabaseUtils
import uuid
import random
import datetime
import secrets
from django.utils.text import slugify


fake = Faker()


class ModelFieldCharaterstics(
    DatabaseUtils,
    StdoutTextTheme
):
    """
        This class examines the characteristics of Django model fields
        and generates random data that adheres to those characteristics.
    """

    def CharField(
            self,
            obj: models.CharField,
            model: models.Model
    ) -> str:
        """
            Generates character data for a model's CharField.

            Args:
                - obj: The CharField instance from the model.
                - model: The Django model class.

            Returns:
                - A character string for the specified model field.
        """
        if obj.choices:
            value = self.get_choices_charfield(obj=obj)
            return str(value)

        if obj.unique or obj.primary_key:
            value = self.get_unique_char_data(model=model, obj=obj)
        else:
            is_title = any(
                field in obj.name
                for field in
                [
                    'name',
                    'title',
                    'username',
                    'user_name'
                ]
            )
            max_chars = 50
            if obj.max_length is not None and (is_title or obj.max_length < 50):
                max_chars = obj.max_length
            elif obj.max_length is not None:
                max_chars = int(obj.max_length) // 2

            value = fake.name() if max_chars < 50 or is_title else fake.text(max_nb_chars=max_chars)
            value = value[:max_chars-1]

        return value

    def TextField(
            self,
            obj: models.TextField,
            model
    ) -> str:
        """
            Generates text data for a model's TextField.

            Args:
                - obj: The TextField instance from the model.
                - model: The Django model class.

            Returns:
                - Text data for the specified model field.
        """

        if obj.unique or obj.primary_key:
            return self.get_unique_char_data(
                model=model,
                obj=obj
            )
        max_chars = 100
        if obj.max_length is not None and obj.max_length < 50:
            max_chars = obj.max_length
        elif obj.max_length is not None:
            max_chars = int(obj.max_length)/2
        value = fake.text(
            max_nb_chars=max_chars
        )

        return value

    def EmailField(
            self,
            obj: models.CharField,
            model
    ) -> str:
        """
            Generates email data for a model's EmailField.

            Args:
                - obj: The EmailField instance from the model.
                - model: The Django model class.

            Returns:
                - An email address for the specified model field.
        """

        if obj.unique or obj.primary_key:
            value = self.get_unique_value(
                model=model,
                obj=obj,
                value=fake.email
            )
        else:
            return fake.email()

        return value

    def IntegerField(
        self,
        obj: models.IntegerField,
        model: models.Model
    ) -> int:
        """
        Generates integer data for a model's IntegerField.

        Args:
            - obj: The IntegerField instance from the model.
            - model: The Django model class.

        Returns:
            - An integer value for the specified model field.
        """

        return int(self.generate_numeric_value(obj=obj, model=model))

    def DecimalField(
            self,
            obj: models.DecimalField,
            model: models.Model
    ) -> float:
        """
        Generates decimal data for a model's DecimalField.

        Args:
            - obj: The DecimalField instance from the model.
            - model: The Django model class.

        Returns:
            - A decimal value for the specified model field.
        """

        if obj.unique or obj.primary_key:
            return self.get_unique_numeric_field_data(
                obj=obj,
                model=model
            )

        # ? Generate a random decimal with max_digits and decimal_places
        max_digit, decimal_places, max_length = obj.max_digits, obj.decimal_places, obj.max_length

        if max_length is None and max_digit is None and decimal_places is None:

            max_length, max_digit, decimal_places = 7, 5, 2
        elif max_length is None and (max_digit is not None and decimal_places is not None):
            max_digit = max_digit - decimal_places
            max_length = max_digit + decimal_places
        max_digit, decimal_places, max_length = max_digit-1, decimal_places-1, max_length-1
        value = random.randint(0, 10**decimal_places - 1)
        return value

    def BooleanField(
        self,
        obj: models.BooleanField,
        model: models.Model
    ) -> bool:
        """
        Generates boolean data for a model's BooleanField.

        Args:
            - obj: The BooleanField instance from the model.
            - model: The Django model class.

        Returns:
            - A boolean value for the specified model field.
        """

        return fake.boolean()

    def UUIDField(
        self,
        obj: models.UUIDField,
        model: models.Model
    ) -> uuid.UUID:
        """
        Generates UUID data for a model's UUIDField.

        Args:
            - obj: The UUIDField instance from the model.
            - model: The Django model class.

        Returns:
            - A UUID value for the specified model field.
        """

        val = fake.uuid4()
        filter_set = {obj.name: val}
        if (obj.unique or obj.primary_key) and model.objects.filter(**filter_set).exists():
            return self.UUIDField(obj=obj, model=model)

        return val

    def FloatField(
        self,
        obj: models.FloatField,
        model: models.Model
    ) -> float:
        """
        Generates float data for a model's FloatField.

        Args:
            - obj: The FloatField instance from the model.
            - model: The Django model class.

        Returns:
            - A float value for the specified model field.
        """

        return float(
            self.generate_numeric_value(
                obj=obj,
                model=model
            )
        )

    def PositiveBigIntegerField(
        self,
        obj: models.PositiveBigIntegerField,
        model: models.Model
    ) -> int:
        """
        Generates integer data for a model's PositiveBigIntegerField.

        Args:
            - obj: The PositiveBigIntegerField instance from the model.
            - model: The Django model class.

        Returns:
            - A positive integer value for the specified model field.
        """

        return int(
            self.generate_numeric_value(
                obj=obj,
                model=model
            )
        )

    def PositiveIntegerField(
        self,
        obj: models.PositiveIntegerField,
        model: models.Model
    ) -> int:
        """
        Generates integer data for a model's PositiveIntegerField.

        Args:
            - obj: The PositiveIntegerField instance from the model.
            - model: The Django model class.

        Returns:
            - A positive integer value for the specified model field.
        """

        return int(
            self.generate_numeric_value(
                obj=obj,
                model=model
            )
        )

    def PositiveSmallIntegerField(
        self,
        obj: models.PositiveSmallIntegerField,
        model: models.Model
    ) -> int:
        """
        Generates integer data for a model's PositiveSmallIntegerField.

        Args:
            - obj: The PositiveSmallIntegerField instance from the model.
            - model: The Django model class.

        Returns:
            - A positive small integer value for the specified model field.
        """

        return int(
            self.generate_numeric_value(
                obj=obj,
                model=model
            )
        )

    def DateField(
        self,
        obj: models.DateField,
        model: models.Model
    ) -> datetime.datetime.date:
        """
        Generates a random date for a model's DateField.

        Args:
            - obj: The DateField instance from the model.
            - model: The Django model class.

        Returns:
            - A random date for the specified model field.
        """

        return fake.date_this_decade()

    def DateTimeField(
        self,
        obj: models.DateTimeField,
        model: models.Model
    ) -> datetime.datetime.now:
        """
        Generates a random datetime for a model's DateTimeField.

        Args:
            - obj: The DateTimeField instance from the model.
            - model: The Django model class.

        Returns:
            - A random datetime value for the specified model field.
        """

        return fake.date_time_this_decade()

    def TimeField(
        self,
        obj: models.TimeField,
        model: models.Model
    ) -> datetime.time:
        """
        Generates a random time for a model's TimeField.

        Args:
            - obj: The TimeField instance from the model.
            - model: The Django model class.

        Returns:
            - A random time value for the specified model field.
        """

        hour = random.randint(0, 23)
        minute = random.randint(0, 59)
        second = random.randint(0, 59)
        microsecond = random.randint(0, 999999)

        return datetime.time(hour, minute, second, microsecond)

    def SlugField(
        self,
        obj: models.SlugField,
        model: models.Model
    ) -> str:
        """
            Generates a random slug for a model's SlugField.

            Args:
                - obj: The SlugField instance from the model.
                - model: The Django model class.

            Returns:
                - A random slug value for the specified model field.
        """
        if obj.unique or obj.primary_key:
            return slugify(
                self.get_unique_value(
                    obj=obj,
                    model=model,
                    value=fake.slug
                )
            )
        return slugify(fake.slug())

    def URLField(
        self,
        obj: models.URLField,
        model: models.Model
    ) -> str:
        """
            Generates a random URL for a model's URLField.

            Args:
                - obj: The URLField instance from the model.
                - model: The Django model class.

            Returns:
                - A random URL value for the specified model field.
        """

        if obj.unique or obj.primary_key:
            return self.get_unique_value(
                obj=obj,
                model=model,
                value=fake.url
            )
        return fake.url()

    def IPAddressField(
        self,
        obj: models.IPAddressField,
        model: models.Model
    ) -> str:
        """
        Generates a random IPv4 address for a model's IPAddressField.

        Args:
            - obj: The IPAddressField instance from the model.
            - model: The Django model class.

        Returns:
            - A random IPv4 address for the specified model field.
        """

        if obj.unique or obj.primary_key:
            return self.get_unique_value(
                obj=obj,
                model=model,
                value=fake.ipv4
            )
        return fake.ipv4()

    def GenericIPAddressField(
        self,
        obj: models.GenericIPAddressField,
        model: models.Model
    ) -> str:
        """
        Generates a random IP address (IPv4 or IPv6) for a model's GenericIPAddressField.

        Args:
            - obj: The GenericIPAddressField instance from the model.
            - model: The Django model class.

        Returns:
            A random IPv4 or IPv6 address for the specified model field.
        """

        if obj.unique or obj.primary_key:
            return self.get_unique_value(
                obj=obj,
                model=model,
                value=random.choice(
                    [fake.ipv4, fake.ipv6]
                )
            )
        return fake.ipv4()

    def BinaryField(
        self,
        obj: models.BinaryField,
        model: models.Model
    ) -> str:
        """
            Generates random binary data for a model's BinaryField.

            Args:
                - obj: The BinaryField instance from the model.
                - model: The Django model class.

            Returns:
                - Random binary data for the specified model field.
        """

        return secrets.token_bytes(10)

    def DurationField(
        self,
        obj: models.DurationField,
        model: models.Model
    ) -> datetime.timedelta:
        """
            Generates a random time duration for a model's DurationField.

            Args:
                - obj: The DurationField instance from the model.
                - model: The Django model class.

            Returns:
                - A random time duration value for the specified model field.
        """

        if obj.unique or obj.primary_key:
            return self.get_unique_value(
                obj=obj,
                model=model,
                value=self.generate_random_duration
            )
        return self.generate_random_duration()

    def JSONField(
        self,
        obj: models.JSONField,
        model: models.Model
    ) -> dict:
        """
            Generates a random json for a model's JSONField.

            Args:
                - obj: The JSONField instance from the model.
                - model: The Django model class.

            Returns:
                - A random json value for the specified model field.
        """

        return self.create_random_json()
