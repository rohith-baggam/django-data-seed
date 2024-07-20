# myapp/management/commands/populate_fake_data.py
from django.core.management.base import BaseCommand
from .loaddata import SeedData


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
            help='The number of objects to create'
        )

    def handle(self, *args, **kwargs):
        number_of_objects = kwargs.get('no_of_objects_to_create', 10)
        app_name = kwargs.get('django_app', None)
        self.stdout.write(self.style.SUCCESS(
            'Django data seed Started Populating data'))
        run = SeedData()
        run.SeedData(number_of_objects=number_of_objects, app_name=app_name)
        self.stdout.write(self.style.SUCCESS(
            'Successfully populated data'))
