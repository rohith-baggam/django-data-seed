from django.db import models
import uuid
# Create your models here.


class SubAPP1BooleanModel(models.Model):
    boolean_field = models.BooleanField(default=False)


class SubAPP1EmailModel(models.Model):
    email_field = models.EmailField(max_length=254)


class SubAPP1CharModel(models.Model):
    # Define choices as a tuple of tuples
    CHOICES = [
        ('option1', 'Option 1'),
        ('option2', 'Option 2'),
        ('option3', 'Option 3'),
    ]

    char_field = models.CharField(max_length=100)
    choice_field = models.CharField(
        max_length=20, choices=CHOICES, default='option1'
    )


class SubAPP1DecimalModel(models.Model):
    decimal_field = models.DecimalField(max_digits=10, decimal_places=2)


class SubAPP1FloatModel(models.Model):
    float_field = models.FloatField()


class SubAPP1IntegerModel(models.Model):
    integer_field = models.IntegerField()


class SubAPP1UUIDModel(models.Model):
    uuid_field = models.UUIDField(
        default=uuid.uuid4, unique=True)


class SubAPP1PositiveBigIntegerModel(models.Model):
    positive_big_integer_field = models.PositiveBigIntegerField()


class SubAPP1PositiveIntegerModel(models.Model):
    positive_integer_field = models.PositiveIntegerField()


class SubAPP1PositiveSmallIntegerModel(models.Model):
    positive_small_integer_field = models.PositiveSmallIntegerField()


class SubAPP1SmallIntegerModel(models.Model):
    small_integer_field = models.SmallIntegerField()


class SubAPP1BigIntegerModel(models.Model):
    big_integer_field = models.BigIntegerField()


class SubAPP1DateModel(models.Model):
    date_field = models.DateField()


class SubAPP1DateTimeModel(models.Model):
    date_time_field = models.DateTimeField()


class SubAPP1TimeModel(models.Model):
    time_field = models.TimeField()


class SubAPP1TextModel(models.Model):
    text_field = models.TextField()


class SubAPP1SlugModel(models.Model):
    slug_field = models.SlugField(max_length=50)


class SubAPP1URLModel(models.Model):
    url_field = models.URLField(max_length=200)


class SubAPP1IPAddressModel(models.Model):
    ip_address_field = models.GenericIPAddressField()


class SubAPP1GenericIPAddressModel(models.Model):
    generic_ip_address_field = models.GenericIPAddressField()


class SubAPP1BinaryModel(models.Model):
    binary_field = models.BinaryField()


class SubAPP1DurationModel(models.Model):
    duration_field = models.DurationField()


class SubAPP1JSONModel(models.Model):
    json_field = models.JSONField(default=dict)


class SubAPP1ForeignKeyModel(models.Model):
    uuid_field = models.ForeignKey(
        SubAPP1UUIDModel, on_delete=models.CASCADE,
        related_name="SubAPP1ForeignKeyModel_char_field"
    )
    integer_field = models.ForeignKey(
        SubAPP1IntegerModel, on_delete=models.CASCADE,
        related_name="SubAPP1ForeignKeyModel_integer_field"
    )
    self_field = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        related_name="SubAPP1ForeignKeyModel_self",
        null=True,
        blank=True
    )


class SubAPP1OneToOneModel(models.Model):
    uuid_field = models.OneToOneField(
        SubAPP1UUIDModel, on_delete=models.CASCADE,
        related_name="SubAPP1OneToOneModel_char_field"
    )


class SubAPP1ManyToManyModel(models.Model):
    uuid_field = models.ManyToManyField(
        SubAPP1UUIDModel,
        related_name="SubAPP1ManyToManyModel_char_field"
    )
