import os
from django.apps import apps
from django.conf import settings


def get_all_custom_apps_and_sub_apps(specific_app_name=None):
    """
    Retrieves all custom apps and sub-apps in the Django project by inspecting the INSTALLED_APPS and their directory structure.
    Excludes third-party and Django default apps.
    """
    project_root = os.path.abspath(settings.BASE_DIR)
    all_custom_apps = []

    for app_config in apps.get_app_configs():
        app_path = app_config.path
        app_name = app_config.name

        # ? Check if the app is inside the project directory
        if app_path.startswith(project_root):
            #  ? Add the main app
            all_custom_apps.append(app_name)

            # ? Recursively find sub-apps
            for root, dirs, files in os.walk(app_path):
                if 'models.py' in files and root != app_path:
                    # ? This is likely a sub-app
                    relative_path = os.path.relpath(root, project_root)
                    sub_app_name = relative_path.replace(os.path.sep, '.')

                    # ? Extract the app label from the sub-app name
                    sub_app_label = sub_app_name.split('.')[-1]
                    all_custom_apps.append(sub_app_label)

    if specific_app_name:
        # ? Filter to include only the specified app and its sub-apps
        all_custom_apps = [
            app for app in all_custom_apps
            if app == specific_app_name or app.startswith(specific_app_name + '.')
        ]

    return all_custom_apps


def get_filtered_models(installed_apps=None, model_name=None, specific_app_name=None):

    if specific_app_name and model_name:
        return []

    if installed_apps is None:
        installed_apps = get_all_custom_apps_and_sub_apps(specific_app_name)

    models = [
        model for model in apps.get_models()
        if model._meta.app_label in installed_apps and (not model_name or model.__name__ == model_name)
    ]

    if not models:
        print(
            f"No models found for {'app ' + specific_app_name if specific_app_name else ''} {'model ' + model_name if model_name else ''}.")

    return models
