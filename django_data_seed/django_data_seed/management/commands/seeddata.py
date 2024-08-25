from django.core.management.base import BaseCommand
from .load_data import SeedData


class Command(BaseCommand):
    help = 'Populates the database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--no-of-objects-to-create',
            type=int,
            default=10,
            help='The number of objects to create'
        )

        parser.add_argument(
            '--django-app',
            type=str,
            default=None,
            help='Specify the app to loads'
        )

        parser.add_argument(
            '--django-model',
            type=str,
            default=None,
            help='Specify the model to load'
        )

    def handle(self, *args, **kwargs):
        number_of_objects = kwargs.get(
            'no_of_objects_to_create',
            10
        )
        app_name = kwargs.get(
            'django_app',
            None
        )
        model_name = kwargs.get(
            'django_model',
            None
        )

        self.stdout.write(
            self.style.SUCCESS(
                'Django data seed Started Populating data'
            )
        )
        run = SeedData()
        run.SeedData(
            number_of_objects=number_of_objects, app_name=app_name,
            model_name=model_name
        )
        self.stdout.write(self.style.SUCCESS(
            'Successfully populated data'))
