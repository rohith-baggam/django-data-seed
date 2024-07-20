from .colorama_theme import StdoutTextTheme
from django.db import models
from faker import Faker
from .utils import DatabaseUtils
import uuid
import random
import datetime
import secrets
from django.utils.text import slugify
from decimal import Decimal
from .utils import SUPPORTED_DJANGO_MODEL_FIELDS
models.BigAutoField

fake = Faker()


class ModelFieldCharaterstics(
    DatabaseUtils,
    StdoutTextTheme
):
    """
        This Class reads django models field charaterstics
        and create random data with those charaterstics
    """

    def CharField(
            self,
            obj: models.CharField,
            model
    ) -> str:
        """
            Generates character data for a model CharField.

            Args:
            - obj: The model CharField object.
            - model: The Django model class.

            Returns:
            - Character data for the model field.
        """

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
            Generates character data for a model TextField.

            Args:
            - obj: The model TextField object.
            - model: The Django model class.

            Returns:
            - Character data for the model field.
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
            Generates Email data for a model EmailField.

            Args:
            - obj: The model EmailField object.
            - model: The Django model class.

            Returns:
            - Email data for the model field.
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
            Generates integer data for a model IntegerField.

            Args:
            - obj: The model IntegerField object.
            - model: The Django model class.

            Returns:
            - integer data for the model field.
        """
        return int(self.generate_numeric_value(obj=obj, model=model))

    def DecimalField(
            self,
            obj: models.DecimalField,
            model: models.Model
    ) -> float:
        """
            Generates decimal data for a model DecimalField.

            Args:
            - obj: The model DecimalField object.
            - model: The Django model class.

            Returns:
            - decimal data for the model field.
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
            Generates boolean data for a model BooleanField.

            Args:
            - obj: The model BooleanField object.
            - model: The Django model class.

            Returns:
            - boolean data for the model field.
        """
        return fake.boolean()

    def UUIDField(
        self,
        obj: models.UUIDField,
        model: models.Model
    ) -> uuid.UUID:
        """
            Generates uuid data for a model UUIDField.

            Args:
            - obj: The model UUIDField object.
            - model: The Django model class.

            Returns:
            - uuid data for the model field.
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
            Generates Float data for a model FloatField.

            Args:
            - obj: The model FloatField object.
            - model: The Django model class.

            Returns:
            - decimal Float for the model field.
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
            Generates integer data for a model PositiveBigIntegerField.

            Args:
            - obj: The model PositiveBigIntegerField object.
            - model: The Django model class.

            Returns:
            - integer data for the model field.
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
            Generates integer data for a model PositiveIntegerField.

            Args:
            - obj: The model PositiveIntegerField object.
            - model: The Django model class.

            Returns:
            - integer data for the model field.
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
            Generates integer data for a model PositiveSmallIntegerField.

            Args:
            - obj: The model PositiveSmallIntegerField object.
            - model: The Django model class.

            Returns:
            - integer data for the model field.
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
            Generates random date for a model DateField.

            Args:
            - obj: The model DateField object.
            - model: The Django model class.

            Returns:
            - random date for the model field.
        """
        return fake.date_this_decade()

    def DateTimeField(
        self,
        obj: models.DateTimeField,
        model: models.Model
    ) -> datetime.datetime.now:
        """
            Generates random date for a model DateTimeField.

            Args:
            - obj: The model DateTimeField object.
            - model: The Django model class.

            Returns:
            - random datetime for the model field.
        """
        return fake.date_time_this_decade()

    def TimeField(
        self,
        obj: models.TimeField,
        model: models.Model
    ) -> datetime.time:
        """
            Generates random date for a model TimeField.

            Args:
            - obj: The model TimeField object.
            - model: The Django model class.

            Returns:
            - random time for the model field.
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
            Generates random slug for a model SlugField.

            Args:
            - obj: The model SlugField object.
            - model: The Django model class.

            Returns:
            - random slug value for the model field.
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
            Generates random slug for a model URLField.

            Args:
            - obj: The model URLField object.
            - model: The Django model class.

            Returns:
            - random url value for the model field.
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
            Generates random slug for a model IPAddressField.

            Args:
            - obj: The model IPAddressField object.
            - model: The Django model class.

            Returns:
            - random Ipv4 address  value for the model field.
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
            Generates random slug for a model GenericIPAddressField.

            Args:
            - obj: The model GenericIPAddressField object.
            - model: The Django model class.

            Returns:
            - random Ipv4, Ipv6 address  value for the model field.
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
            Generates random binnary for a model BinaryField.

            Args:
            - obj: The model BinaryField object.
            - model: The Django model class.

            Returns:
            - random binnary  value for the model field.
        """

        return secrets.token_bytes(10)

    def DurationField(
        self,
        obj: models.DurationField,
        model: models.Model
    ) -> datetime.timedelta:
        """
            Generates random slug for a model DurationField.

            Args:
            - obj: The model DurationField object.
            - model: The Django model class.

            Returns:
            - random time duration value for the model field.
        """
        if obj.unique or obj.primary_key:
            return self.get_unique_value(
                obj=obj,
                model=model,
                value=self.generate_random_duration
            )
        return self.generate_random_duration()
