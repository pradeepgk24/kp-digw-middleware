from middleware.common.helpers.local_cache import lru_cache_with_ttl
from middleware.common.metadatabase.clients.meta_database_client import MetaDatabaseClient
from middleware.common.metadatabase.model.difw_metadb_model import ProjectAccountSettings, ProjectProperties, Subjects
from middleware.common.metadatabase.model.types.project_account_types_enum import ProjectAccountTypesEnum

class ProjectSettingsMetadataProvider(MetaDatabaseClient):
    """
    Database client which served actions related with project settings
    """

    def insert_or_update_project_account_settings(self, project_account_settings: ProjectAccountSettings, user_id: str):
        """
        Insert or update project account settings

        @param project_account_settings: subject which will be either created or updated
        @param user_id: user who create/update the project account settings

        @return: inserted or updated project account settings
        """
        return self.insert_or_update_record(project_account_settings, user_id)

    def insert_project_account_settings(self, project_account_settings: ProjectAccountSettings, user_id: str):
        """
        Creates project account settings in MetaDB.

        @param project_account_settings:
        @param user_id:
        @return:
        """
        return self.insert_record(project_account_settings, user_id)

    def update_project_account_settings(self, project_account_settings: ProjectAccountSettings, user_id: str):
        """
        Update existing project account settings

        @param project_account_settings:
        @param user_id: user who update the project account settings
        @return: updated project account settings
        """
        return self.update_record(project_account_settings, user_id)

    @lru_cache_with_ttl(ttl=15)
    def get_project_account_settings(self, project_id: str, account_type: ProjectAccountTypesEnum):
        """
        Get project account settings

        @param project_id:
        @param account_type:
        @return:
        """
        self.logger.info(
            f"Going to get project accounts settings of type {account_type} for project with id {project_id}")
        return ProjectAccountSettings(PROJECT_ID=project_id, ACCOUNT_TYPE=account_type).get_unique(self.session)

    def insert_or_update_project_general_settings(self, project_general_settings: ProjectProperties, user_id: str,
                                                  subject: Subjects):
        """
        Insert or update project general settings

        @param project_general_settings: general setting which will be either created or updated
        @param user_id: user who create/update the project general settings
        @param subject

        @return: inserted or updated project general settings
        """
        self.enrich_with_updating_audit_columns(project_general_settings, user_id)
        self.update_record(subject, user_id, commit=False)
        self.insert_or_update_record(project_general_settings, user_id, commit=False)
        # issue commit only both the transactions are complete
        return self.session.commit()

    def insert_project_general_setting(self, project_general_setting: ProjectProperties, user_id: str):
        """
        Creates project general settings in MetaDB.

        @param project_general_setting:
        @param user_id:
        @return:
        """
        return self.insert_record(project_general_setting, user_id)

    def update_project_general_setting(self, project_general_setting: ProjectProperties, user_id: str):
        """
        Update existing project general setting

        @param project_general_setting
        @param user_id: user who update the project general settings
        @return: updated project general settings
        """
        return self.update_record(project_general_setting, user_id)

    def get_project_general_settings(self, project_id: str) -> [ProjectProperties]:
        """
        Get project general settings

        @param project_id:
        @return:
        """
        self.logger.info(f"Going to get project general settings for project with id {project_id}")
        return ProjectProperties(PROJECT_ID=project_id).get_unique(self.session)
