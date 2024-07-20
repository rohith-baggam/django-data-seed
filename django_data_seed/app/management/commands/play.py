# myapp/management/commands/my_custom_command.py

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Execute my custom function'

    def handle(self, *args, **kwargs):
        self.stdout.write("Running my custom function...")
        # from django.db import models
        # obj_str = "AutoField"

        # # Use getattr to get the AutoField class from the models module
        # actual_object = getattr(models, obj_str)

        # # Now actual_object contains the AutoField class from Django's models
        # print(actual_object)
        # from permissions.models import PermissionsModel
        # fields = PermissionsModel._meta.get_fields()
        # import inspect
        # print(fields[-2].max_length)
        # print(callable(fields[-2]))
        # print(type(fields[-2]))
        from django.core.validators import MinValueValidator, MaxValueValidator
        from configurations.miscellaneous.models import ConfigurationMiscellaneousMeasurementModel
        # Assuming `ConfigurationMiscellaneousMeasurementModel` is your model
        fields = ConfigurationMiscellaneousMeasurementModel._meta.get_fields()
        sort_key_field = None

        # Find the 'sort_key' field
        for field in fields:
            if field.name == "sort_key":
                sort_key_field = field
                break

        if sort_key_field:
            min_value = None
            max_value = None

            # Iterate through validators and extract MinValueValidator and MaxValueValidator values
            for validator in sort_key_field.validators:
                if isinstance(validator, MinValueValidator):
                    min_value = validator.limit_value
                elif isinstance(validator, MaxValueValidator):
                    max_value = validator.limit_value

            print(f"Min value: {min_value}")
            print(f"Max value: {max_value}")
        else:
            print("Field 'sort_key' not found.")

        self.stdout.write(
            self.style.SUCCESS(
                'Function executed successfully'
            )
        )


# if field_type == 'CharField':
#         print(f"Max Length:   {field.max_length}")
#         print(f"Null Allowed: {field.null}")
#         print(f"Blank Allowed:{field.blank}")
#         print(f"Default Value:{field.default}")
#         print(f"Verbose Name: {field.verbose_name}")
#         print(f"Unique:       {field.unique}")
#         print(f"Help Text:    {field.help_text}")
#     elif field_type == 'IntegerField':
#         print(f"Null Allowed: {field.null}")
#         print(f"Blank Allowed: {field.blank}")
#         print(f"Default Value: {field.default}")
#         print(f"Verbose Name: {field.verbose_name}")
#         print(f"Primary Key: {field.primary_key}")
#     elif field_type == 'DecimalField':
#         print(f"Max Digits: {field.max_digits}")
#         print(f"Decimal Places: {field.decimal_places}")
#         print(f"Null Allowed: {field.null}")
#         print(f"Blank Allowed: {field.blank}")
#         print(f"Default Value: {field.default}")
#         print(f"Verbose Name: {field.verbose_name}")
#         print(f"Unique: {field.unique}")
#         print(f"Help Text: {field.help_text}")
