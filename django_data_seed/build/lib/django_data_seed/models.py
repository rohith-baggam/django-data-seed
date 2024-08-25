from .utils.signal_utils import (
    data_backup_pre_save_handler,
    data_logentry_prev_save_handler,
    data_logentry_post_save_handler
)
from django.conf import settings
from django.dispatch import receiver
from django.db.models.signals import (
    pre_delete,
    pre_save,
    post_save
)
from django.db import models
import uuid
from django.contrib.auth import get_user_model
from typing import Type
from .utils.colorama_theme import StdoutTextTheme
from .utils.thread_locals import (
    set_thread_variable,
    clear_thread_variable
)
from django_data_seed.utils.excluded_models import (
    auto_log_entry_get_excluded_models,
    auto_data_backup_get_excluded_models
)
colorma_theme = StdoutTextTheme()


class DjangoSeedDataBackUpModel(models.Model):
    data = models.JSONField()
    created_at = models.DateTimeField(
        auto_now_add=True,
        null=True
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        null=True
    )
    object_id = models.CharField(
        max_length=100,
        null=True,
        blank=True
    )
    model_name = models.CharField(
        max_length=255,
        null=True,
        blank=True
    )
    deleted_by = models.ForeignKey(
        get_user_model(),
        on_delete=models.SET_NULL,
        related_name="DjangoSeedDataBackUpModel_deleted_by",
        null=True,
        blank=True
    )


class DjangoSeedDataLogEntryModel(models.Model):
    before_mutation = models.JSONField(null=True, blank=True)
    after_mutation = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(
        auto_now_add=True,
        null=True
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        null=True
    )
    object_id = models.CharField(
        max_length=100,
        null=True,
        blank=True
    )
    model_name = models.CharField(
        max_length=255,
        null=True,
        blank=True
    )
    mutated_by = models.ForeignKey(
        get_user_model(),
        on_delete=models.SET_NULL,
        related_name="DjangoSeedDataLogEntryModel_mutated_by",
        null=True,
        blank=True
    )


@receiver(pre_delete)
def data_seed_backup_data_before_delete_handler(sender: Type[models.Model], instance: models.Model, **kwargs):
    """
        Handles the `pre_delete` signal to back up data before a model instance is deleted.

        Args:
            sender (Type[models.Model]): The model class that sent the signal.
            instance (models.Model): The instance of the model that is about to be deleted.
            **kwargs: Additional keyword arguments provided by the signal.

        Description:
            This signal handler is triggered before a model instance is deleted from the database.
            It is used to create a backup of the instance's data to a backup model to ensure that
            information is preserved even after the instance is removed.

        Returns:
            None
    """
    try:
        if sender.__name__ in auto_data_backup_get_excluded_models():
            return
        ENABLE_DJANGO_DATA_SEED_AUTO_BACKUP = getattr(
            settings, 'ENABLE_DJANGO_DATA_SEED_AUTO_BACKUP', None)
        if not ENABLE_DJANGO_DATA_SEED_AUTO_BACKUP:
            return
        data_dict = data_backup_pre_save_handler(
            sender=sender, instance=instance)
        # ? Create a backup entry
        DjangoSeedDataBackUpModel.objects.create(**data_dict)
        colorma_theme.stdout_success("Databack up successfully.!")
    except Exception:
        pass


@receiver(pre_save)
def data_seed_auto_log_entry_pre_save_data_handler(sender: Type[models.Model], instance: models.Model, **kwargs):
    """
        Handles the pre-save signal to store the state of a model instance before any mutations.

        Args:
            sender: The model class sending the signal.
            instance: The instance of the model being sent in the signal.
            **kwargs: Additional keyword arguments sent with the signal (e.g., `update_fields`).

        Info:
            This signal receiver function is triggered before a model instance is saved. It stores the data
            of the instance prior to any mutations by creating a backup entry. This is useful for
            maintaining historical data or for rollback purposes if needed.

        Returns:
            None: This function does not return any value but performs data storage operations.
    """

    try:
        if sender.__name__ in auto_log_entry_get_excluded_models():
            return
        ENABLE_DJANGO_DATA_SEED_AUTO_LOG_ENTRY = getattr(
            settings, 'ENABLE_DJANGO_DATA_SEED_AUTO_LOG_ENTRY', None)
        if not ENABLE_DJANGO_DATA_SEED_AUTO_LOG_ENTRY:

            return
        # ? only update if any changes happend
        data_dict = data_logentry_prev_save_handler(
            sender=sender,
            instance=instance
        )
        # ? Create a backup entry
        instance = DjangoSeedDataLogEntryModel.objects.create(**data_dict)
        set_thread_variable(
            name="django_data_seed_auto_logentry_pk",
            value=instance.pk
        )
    except Exception as e:
        pass


@receiver(post_save)
def data_seed_auto_log_entry_post_save_data_handler(sender: Type[models.Model], instance: models.Model, **kwargs):
    """
        Handles the `post_save` signal for storing data after a model instance has been saved.

        Args:
            sender (Type[models.Model]): The model class that sent the signal.
            instance (models.Model): The instance of the model that was saved.
            **kwargs: Additional keyword arguments passed by the signal.

        Description:
            This signal handler is triggered after a model instance has been saved to the database. 
            It is used to create or update a log entry with the current state of the model instance 
            to track changes made to the instance.

        Returns:
            None
    """

    try:
        if sender.__name__ in auto_log_entry_get_excluded_models():
            return
        ENABLE_DJANGO_DATA_SEED_AUTO_LOG_ENTRY = getattr(
            settings, 'ENABLE_DJANGO_DATA_SEED_AUTO_LOG_ENTRY', None)
        if not ENABLE_DJANGO_DATA_SEED_AUTO_LOG_ENTRY:

            return
        is_data_saved = data_logentry_post_save_handler(
            sender=sender,
            instance=instance,
            queryset=DjangoSeedDataLogEntryModel.objects.all()
        )
        if is_data_saved:

            colorma_theme.stdout_success("Databack up successfully..!")
        # ? clear the information loaded to threads
        clear_thread_variable('django_data_seed_auto_logentry_pk')
    except Exception as e:
        pass


# * These all are test models


class DjangoDataSeedBooleanModel(models.Model):
    boolean_field = models.BooleanField(default=False)


class DjangoDataSeedEmailModel(models.Model):
    email_field = models.EmailField(max_length=254)


class DjangoDataSeedCharModel(models.Model):
    # Define choices as a tuple of tuples
    CHOICES = [
        ('option1', 'Option 1'),
        ('option2', 'Option 2'),
        ('option3', 'Option 3'),
    ]

    char_field = models.CharField(max_length=100)
    choice_field = models.CharField(
        max_length=20, choices=CHOICES, default='option1')


class DjangoDataSeedDecimalModel(models.Model):
    decimal_field = models.DecimalField(max_digits=10, decimal_places=2)


class DjangoDataSeedFloatModel(models.Model):
    float_field = models.FloatField()


class DjangoDataSeedIntegerModel(models.Model):
    integer_field = models.IntegerField()


class DjangoDataSeedUUIDModel(models.Model):
    uuid_field = models.UUIDField(
        default=uuid.uuid4, unique=True)


class DjangoDataSeedPositiveBigIntegerModel(models.Model):
    positive_big_integer_field = models.PositiveBigIntegerField()


class DjangoDataSeedPositiveIntegerModel(models.Model):
    positive_integer_field = models.PositiveIntegerField()


class DjangoDataSeedPositiveSmallIntegerModel(models.Model):
    positive_small_integer_field = models.PositiveSmallIntegerField()


class DjangoDataSeedSmallIntegerModel(models.Model):
    small_integer_field = models.SmallIntegerField()


class DjangoDataSeedBigIntegerModel(models.Model):
    big_integer_field = models.BigIntegerField()


class DjangoDataSeedDateModel(models.Model):
    date_field = models.DateField()


class DjangoDataSeedDateTimeModel(models.Model):
    date_time_field = models.DateTimeField()


class DjangoDataSeedTimeModel(models.Model):
    time_field = models.TimeField()


class DjangoDataSeedTextModel(models.Model):
    text_field = models.TextField()


class DjangoDataSeedSlugModel(models.Model):
    slug_field = models.SlugField(max_length=50)


class DjangoDataSeedURLModel(models.Model):
    url_field = models.URLField(max_length=200)


class DjangoDataSeedIPAddressModel(models.Model):
    ip_address_field = models.GenericIPAddressField()


class DjangoDataSeedGenericIPAddressModel(models.Model):
    generic_ip_address_field = models.GenericIPAddressField()


class DjangoDataSeedBinaryModel(models.Model):
    binary_field = models.BinaryField()


class DjangoDataSeedDurationModel(models.Model):
    duration_field = models.DurationField()


class DjangoDataSeedJSONModel(models.Model):
    json_field = models.JSONField(default=dict)


class DjangoDataSeedForeignKeyModel(models.Model):
    uuid_field = models.ForeignKey(
        DjangoDataSeedUUIDModel, on_delete=models.CASCADE,
        related_name="DjangoDataSeedForeignKeyModel_char_field"
    )
    integer_field = models.ForeignKey(
        DjangoDataSeedIntegerModel, on_delete=models.CASCADE,
        related_name="DjangoDataSeedForeignKeyModel_integer_field"
    )


class DjangoDataSeedOneToOneModel(models.Model):
    uuid_field = models.OneToOneField(
        DjangoDataSeedUUIDModel, on_delete=models.CASCADE,
        related_name="DjangoDataSeedOneToOneModel_char_field"
    )


class DjangoDataSeedManyToManyModel(models.Model):
    uuid_field = models.ManyToManyField(
        DjangoDataSeedUUIDModel,
        related_name="DjangoDataSeedManyToManyModel_char_field"
    )

# * END OF TEST MODELS
