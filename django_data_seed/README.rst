Django Data Seed is a powerful Django application designed to populate your database with test data. Using the Faker library, it allows you to generate random test data for your models with a single command via [manage.py](http://manage.py/).

## Features

- Generate random data for various Django model fields
- Seed database models with randomly generated data
- Handle complex relationships between models

## **Installation**

To install django-seed, use pip:

```
pip install django-data-seed
```

 Add `django_data_seed` to your `INSTALLED_APPS` in your Django settings:

```json
INSTALLED_APPS = [
    'django_data_seed',
]

```

## Usage

**Note** : The current version of `django-data-seed` works with native Django fields only. It does not support Django Postgres-specific fields.

## **Using with command**

With `django-data-seed`, you can seed your database using a single command. The `seeddata` command is part of the [manage.py](http://manage.py/) script.

- By default django-data-seed populates each model which are configured in [settings.py](http://settings.py) with 10 instances for each model.

```json
python manage.py seeddata 
```

To specify the number of instances to create for each model, use the `--no-of-objects` argument:

```json
python3 manage.py fake_filler --no-of-objects 100
```

To populate data for a specific Django app, use the `--django-app` argument:

```json
python3 manage.py fake_filler --django-app app_name
```

## Supported Versions

### Django Versions

- Django 3.2
- Django 4.0
- Django 4.1

### Python Versions

- Python 3.7
- Python 3.8
- Python 3.9
- Python 3.10

### Operating Systems

- Windows
- macOS
- Linux

## License

This project is licensed under the MIT License - see the [LICENSE](https://www.notion.so/LICENSE) file for details.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request for any changes.

## Support

If you encounter any issues or have any questions, please open an issue on the GitHub repository.visit the 

https://github.com/rohith-baggam/django-data-seed

## Author

Rohith Baggam