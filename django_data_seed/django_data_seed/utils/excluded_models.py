from django.conf import settings

EXCLUDED_MODELS = [
    'DjangoSeedDataBackUpModel',
    'DjangoSeedDataLogEntryModel',
    'LogEntry',
]


def auto_log_entry_get_excluded_models() -> list:
    """
        Retrieves a list of models that should be excluded from automatic log entry.

        Returns:
            list: A list of model classes that are excluded from logging.

        Description:
            This function returns a list of models for which automatic logging is not required.
            It is used to configure which models are excluded from log entry processes.
    """
    excluded_models = EXCLUDED_MODELS
    return excluded_models


def auto_data_backup_get_excluded_models() -> list:
    """
        Retrieves a list of models that should be excluded from automatic data backup.

        Returns:
            list: A list of model classes that are excluded from the data backup process.

        Description:
            This function returns a list of models that are not included in automatic data backup operations.
            It helps in configuring which models should be excluded from the data backup routine.
    """
    excluded_models = EXCLUDED_MODELS
    return excluded_models
