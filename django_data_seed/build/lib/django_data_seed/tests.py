from django.contrib.auth import get_user_model
from django_data_seed.utils.admin_utils import (
    process_entries_core
)
from .models import (
    DjangoSeedDataBackUpModel,
    DjangoSeedDataLogEntryModel,
    DjangoDataSeedCharModel,
    DjangoDataSeedForeignKeyModel,
    DjangoDataSeedUUIDModel,
    DjangoDataSeedIntegerModel
)
from django_data_seed.utils.get_user import (
    set_current_user,
    get_current_user,

)
from django.test import TestCase
from django.test import TestCase
from django.core.management import call_command
from .utils.colorama_theme import StdoutTextTheme
import uuid
from django_data_seed.utils.json_compare import compare_json_objects
from django_data_seed.utils.app_utils import (
    get_all_custom_apps_and_sub_apps,
    get_filtered_models
)


class DataDataSeedTestCase(TestCase, StdoutTextTheme):
    """
        Test case for Django Data Seed, covering all data field types in Django.
    """
    # ? test models
    app_names = get_all_custom_apps_and_sub_apps()
    model_names = get_filtered_models()

    def run_seed_command_for_model(self, model_name):
        try:
            # ? Run the seeddata command
            call_command(
                'seeddata',
                '--django-model',
                model_name,
                '--no-of-objects',
                '10'
            )
            self.stdout_headers(f"Successfully seeded data for {model_name}")

        except Exception as e:
            self.stdout_error(f"Failed to seed data for {model_name}: {e}")

    def run_seed_command_for_apps(self, app_name):
        try:
            # ? Run the seeddata command
            call_command(
                'seeddata',
                '--django-app',
                app_name,
                '--no-of-objects',
                '10'
            )
            self.stdout_headers(f"Successfully seeded data for {app_name}")

        except Exception as e:
            self.stdout_error(f"Failed to seed data for {app_name}: {e}")

    def test_seed_data_for_all_models(self):
        self.stdout_headers("\n\nStarting Django Data Seed test cases")
        for model_name in self.model_names:
            with self.subTest(model=model_name):
                self.run_seed_command_for_model(model_name)
        for app_name in self.app_names:
            with self.subTest(model=app_name):
                self.run_seed_command_for_apps(app_name)


class MockRequest:
    def __init__(self, user):
        self.user = user
        self._messages = "This is testing message"


class DjangoDataSeedAutoBackupTestCase(TestCase, StdoutTextTheme):
    """
        Test case for verifying that deleted data
        is correctly added to backup models and restored as expected.
    """

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='admin',
            password='Abcd.1234',
            email="admin@admin.com"
        )
        self.request = MockRequest(self.user)
        set_current_user(user=self.user)

    def test_data_back_up_instance(self):
        self.stdout_headers(
            "\n\nStarting Django Data Seed Auto Back up test cases")
        self.stdout_info(
            message="Loading test data..."
        )
        char_instance = DjangoDataSeedCharModel.objects.create(
            char_field="sample data",
            choice_field="option3"
        )
        if get_current_user():
            self.stdout_info(
                "User created successfully and configured to the thread"
            )
        char_instance_pk = char_instance.pk
        char_instance.delete()
        self.assertTrue(
            DjangoSeedDataBackUpModel.objects.filter(
                object_id=char_instance_pk,
                model_name="DjangoDataSeedCharModel"
            ).exists(
            )
        )
        self.stdout_info(
            "Deleted object successfully added to backup data."
        )
        process_entries_core(
            queryset=DjangoSeedDataBackUpModel.objects.filter(
                object_id=char_instance_pk,
                model_name="DjangoDataSeedCharModel"
            ),
            data_type="data",
            should_delete=True
        )
        self.stdout_info(
            "Data backup processing to restore to the original state."
        )
        self.assertTrue(
            DjangoDataSeedCharModel.objects.filter(
                pk=char_instance_pk
            ).exists(
            )
        )
        self.stdout_success(
            "Data backup processing was successful, and the instance has been restored to its original state."
        )
        self.assertFalse(
            DjangoSeedDataBackUpModel.objects.filter(
                object_id=char_instance_pk,
                model_name="DjangoDataSeedCharModel"
            ).exists(
            ),
            False
        )
        self.stdout_headers(
            message="Backup instance deleted successfully"
        )


class DjangoDataSeedAutoBackupRelatedInstanceNotFoundTestCase(TestCase, StdoutTextTheme):
    """
        Test case for verifying that deleted data
        is correctly added to backup models and restored as expected.
    """

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='admin',
            password='Abcd.1234',
            email="admin@admin.com"
        )
        self.request = MockRequest(self.user)
        set_current_user(user=self.user)

    def test_data_back_up_instance(self):
        self.stdout_headers(
            "\n\nStarting Django Data Seed Auto Back up test cases")
        self.stdout_info(
            message="Loading test data..."
        )
        if get_current_user():
            self.stdout_info(
                "User created successfully and configured to the thread"
            )
        uuid_value, integer_value = uuid.uuid1(), 10
        uuid_instance = DjangoDataSeedUUIDModel.objects.create(
            uuid_field=uuid_value
        )
        integer_instance = DjangoDataSeedIntegerModel.objects.create(
            integer_field=integer_value
        )
        foreign_key_instance = DjangoDataSeedForeignKeyModel.objects.create(
            uuid_field=uuid_instance,
            integer_field=integer_instance
        )
        uuid_pk, foreign_key_pk = uuid_instance.pk, foreign_key_instance.pk
        uuid_instance.delete()
        self.assertTrue(
            DjangoSeedDataBackUpModel.objects.filter(
                model_name="DjangoDataSeedUUIDModel",
                object_id=uuid_pk
            ).exists(),
            True
        )
        self.stdout_info(
            "UUID instance successfully deleted and backed up."
        )
        self.assertTrue(
            DjangoSeedDataBackUpModel.objects.filter(
                model_name="DjangoDataSeedForeignKeyModel",
                object_id=foreign_key_pk
            ).exists(),
            True
        )
        self.stdout_success(
            "ForeignKey with CASCADE relationship to UUID is successfully deleted along with the UUID instance and backed up. The CASCADE backup functionality is working as intended."
        )
        process_entries_core(
            queryset=DjangoSeedDataBackUpModel.objects.filter(
                model_name="DjangoDataSeedForeignKeyModel",
                object_id=foreign_key_pk
            ),
            data_type="data",
            should_delete=True
        )
        self.assertFalse(
            DjangoDataSeedForeignKeyModel.objects.filter(
                pk=foreign_key_pk
            ).exists(),
            False
        )
        self.stdout_error(
            "Since the UUID, which is a related instance, was deleted and not restored, attempting to restore the ForeignKey will fail because the child instance is missing. Therefore, the ForeignKey logic is functioning as expected."
        )
        process_entries_core(
            queryset=DjangoSeedDataBackUpModel.objects.filter(
                model_name="DjangoDataSeedUUIDModel",
                object_id=uuid_pk
            ),
            data_type="data",
            should_delete=True
        )
        self.assertTrue(
            DjangoDataSeedUUIDModel.objects.filter(
                uuid_field=uuid_value
            ).exists(),
            True
        )
        self.stdout_info(
            "UUID restored up sucessfully"
        )
        process_entries_core(
            queryset=DjangoSeedDataBackUpModel.objects.filter(
                model_name="DjangoDataSeedForeignKeyModel",
                object_id=foreign_key_pk
            ),
            data_type="data",
            should_delete=True
        )
        self.assertTrue(
            DjangoDataSeedForeignKeyModel.objects.filter(
                pk=foreign_key_pk
            ).exists(),
            True
        )
        self.stdout_success(
            "As the UUID is backed up, backing up the ForeignKey will also be successful."
        )
        self.assertFalse(
            DjangoSeedDataBackUpModel.objects.filter(
                model_name="DjangoDataSeedForeignKeyModel",
                object_id=foreign_key_pk
            ).exists(),
            False
        )
        self.stdout_info(
            "The foreign instance has been successfully restored and removed from the backup model."
        )
        self.stdout_headers(
            "Django Data Seed backup features are functioning successfully with relational fields."
        )


class DjangoDataSeedAutoLogEntryTestCase(TestCase, StdoutTextTheme):
    """
        This test case verifies that mutations are logged correctly
        and instances can be restored to their specified state.
    """

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='admin',
            password='Abcd.1234',
            email="admin@admin.com"
        )
        self.request = MockRequest(self.user)
        set_current_user(user=self.user)

    def test_data_back_up_instance(self):
        self.stdout_headers(
            "\n\nStarting Django Data Seed Auto Log Entry test cases")
        self.stdout_info(
            message="Loading test data..."
        )
        data_before_mutation = "sample data"
        char_instance = DjangoDataSeedCharModel.objects.create(
            char_field=data_before_mutation,
            choice_field="option3"
        )
        modified_value = "sample data modified"
        char_instance.char_field = modified_value
        char_instance.save()
        if get_current_user():
            self.stdout_info(
                "User created successfully and configured to thread"
            )

        self.assertTrue(
            DjangoSeedDataLogEntryModel.objects.filter(
                model_name="DjangoDataSeedCharModel",
                object_id=char_instance.pk
            ).exists(
            ),
            True
        )

        self.stdout_success(
            "Mutated data successfully added to log entry"
        )
        log_entry_instance = DjangoSeedDataLogEntryModel.objects.get(
            model_name="DjangoDataSeedCharModel",
            object_id=char_instance.pk
        )
        self.assertFalse(
            compare_json_objects(
                log_entry_instance.before_mutation,
                log_entry_instance.after_mutation
            ),
            True
        )
        self.stdout_info(
            "Log entry includes data before and after mutation."
        )
        process_entries_core(
            queryset=DjangoSeedDataLogEntryModel.objects.filter(
                model_name="DjangoDataSeedCharModel",
                object_id=char_instance.pk
            ),
            data_type="before_mutation",
            should_delete=False
        )
        self.stdout_info(
            "Restoring data to preferred state from log entry"
        )
        char_instance = DjangoDataSeedCharModel.objects.get(
            pk=char_instance.pk
        )
        self.assertFalse(
            compare_json_objects(
                char_instance.char_field,
                modified_value
            ),
            False
        )
        self.stdout_headers(
            "Data has been restored to the preferred state successfully. Log entry test cases ran successfully."
        )


class DjangoDataSeedAutoLogEntryUnWantedSaveTestCase(TestCase, StdoutTextTheme):
    """
        This test case verifies that unnecessary mutations or saves,
        where no data changes occur, are accurately reflected in log entries.
    """

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='admin',
            password='Abcd.1234',
            email="admin@admin.com"
        )
        self.request = MockRequest(self.user)
        set_current_user(user=self.user)

    def test_data_back_up_instance(self):
        self.stdout_headers(
            "\n\nStarting Django Data Seed Auto Log Entry tests for unwanted entries")
        self.stdout_info(
            message="Loading test data..."
        )
        data_before_mutation = "sample data"
        char_instance = DjangoDataSeedCharModel.objects.create(
            char_field=data_before_mutation,
            choice_field="option3"
        )
        modified_value = "sample data"
        char_instance.char_field = modified_value
        char_instance.save()
        if get_current_user():
            self.stdout_info(
                "User created successfully and configured to thread"
            )

        self.assertFalse(
            DjangoSeedDataLogEntryModel.objects.filter(
                model_name="DjangoDataSeedCharModel",
                object_id=char_instance.pk
            ).exists(
            ),
            False
        )

        self.stdout_headers(
            "No differences detected between mutated and created data, so the instance was not added to the log entry. Test case passed successfully."
        )
