# myapp/management/commands/populate_fake_data.py
from django.core.management.base import BaseCommand
from .loaddata import LoadRandomData


class Command(BaseCommand):
    help = 'Populates the database with fake data'

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
        print('kwargs', kwargs)
        # return
        app_name = kwargs.get('django_app', None)
        print('number_of_objects', number_of_objects)
        self.stdout.write(self.style.SUCCESS(
            'Started Populating data'))
        run = LoadRandomData()
        run.loaddata(number_of_objects=number_of_objects, app_name=app_name)
        self.stdout.write(self.style.SUCCESS(
            'Successfully populated fake data'))
