**Django Data Seed** is a powerful Django application designed to simplify the process of populating your database with realistic test data. By leveraging the Faker library, this package allows you to effortlessly generate random data for your models using a single command via `manage.py`. It is especially beneficial for developers who need diverse datasets to ensure comprehensive test coverage and data integrity.

## Features

- **Comprehensive Data Generation**: Generate random, realistic data for a wide range of Django model fields.
- **Simple Seeding Process**: Seed your database models with randomly generated data using a single command.
- **Complex Relationship Handling**: Seamlessly manage complex relationships between different models.
- **Data Backup and Restoration**: Automatically back up deleted instances and restore them when needed.
- **Detailed Log Entries**: Maintain detailed log entries for instance mutations, allowing you to track changes over time.

## New in Version 0.3.0

### Data Backup Feature

Ensure data safety with the new automatic backup feature. When an instance is deleted, it is stored in the `DjangoSeedDataBackUpModel`. This feature can be enabled in your settings:

```python

ENABLE_DJANGO_DATA_SEED_AUTO_BACKUP = True
```

To disable, set the variable to `False` or remove it entirely. You can restore deleted instances from the Django admin panel by selecting the deleted instance and choosing the "Restore data" option.

![Screenshot 2024-08-04 at 5.04.41 PM.png](https://prod-files-secure.s3.us-west-2.amazonaws.com/1eec8b1f-b9a1-4749-9fb6-c138820ac100/1847f03c-b2af-4d20-8a82-6d5ac7351cf5/Screenshot_2024-08-04_at_5.04.41_PM.png)

### Log Entries for Instance Mutations

Track every change made to your instances with detailed log entries. This feature stores both pre- and post-mutation states of an instance. Enable this feature by adding the following setting:

```python

ENABLE_DJANGO_DATA_SEED_AUTO_LOG_ENTRY = True
```

Restore any instance to a previous state from the admin panel by selecting the log entry and choosing the "Restore data" option.

![Screenshot 2024-08-04 at 5.04.17 PM.png](https://prod-files-secure.s3.us-west-2.amazonaws.com/1eec8b1f-b9a1-4749-9fb6-c138820ac100/9a691703-e3a5-4972-85df-5a82011cab38/Screenshot_2024-08-04_at_5.04.17_PM.png)

### Authentication Configurations

To record the user responsible for deletions or mutations, add the middleware to your `settings.py`:

```python

MIDDLEWARE = [
    # other middleware's
    ...
    "django_data_seed.middleware.CurrentUserMiddleware
]

```

If the default middleware does not suit your authentication system, create a custom middleware:

```python

from django_data_seed.utils.get_user import set_current_user

class YourCustomMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        set_current_user(request.user)
        response = self.get_response(request)
        return response

```

### Field Generation Updates

- Now supports choices in `CharField` and `JsonField`, allowing for more realistic and varied data generation.

### Enhanced Command Options

- **Target Specific Models**: You can now seed data for a single model using the `django-app` argument in the `manage.py` command:
    
    ```python
    python manage.py seeddata --django-app model_name
    ```
    

## Installation

To install `django-data-seed`, use pip:

```bash
pip install django-data-seed
```

Add `django_data_seed` to your `INSTALLED_APPS` in your Django settings:

```python

INSTALLED_APPS = [
    ...
    'django_data_seed',
    ...
]
```

After adding `django_data_seed` to your `INSTALLED_APPS`, run the following command to apply migrations:

```python
python3 manage.py migrate
```

## Dependencies

The following dependencies are required and will be installed automatically with `django-data-seed`:

- Django (>=3.2)
- Faker (>=8.0.0)
- colorama (>=0.4.6)

You can also install them manually:

```python
pip install Django>=3.2
pip install Faker>=8.0.0
pip install colorama>=0.4.6
```

## Usage

To seed your database, use the `seeddata` command:

```python
python3 manage.py seeddata
```

To specify the number of instances per model:

```python

python3 manage.py seeddata --no-of-objects 100

```

To seed data for a specific Django app:

```python
python3 manage.py seeddata --django-app app_name
```

To seed data for a specific model:

```python
python3 manage.py seeddata --django-model model_name
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

### Databases

- MySQL
- PostgreSQL
- SQLite

## License

This project is licensed under the MIT License. See the [LICENSE](https://github.com/rohith-baggam/django-data-seed/blob/main/LICENSE) file for details.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request for any changes.

## Support

For any issues or questions, open an issue on the [GitHub repository](https://github.com/rohith-baggam/django-data-seed).

## Author

Rohith Baggam

[LinkedIn Profile](https://www.linkedin.com/in/rohith-raj-baggam/)

---