from middleware.common.entity_management.entities.entity_object import EntityObject
from middleware.common.metadatabase.model.difw_metadb_model import ProjectProperties


class EntityProjectGeneralSettings(EntityObject):
    """
    Entity Project general settings
    """

    def __init__(self, project_id: str, resource_prefix: str, project_group_id: str,
                 jfrog_repository_id: str, description: str = None, display_name: str = None,
                 onboard_email: str = None, onboard_message: str = None,
                 environment: str = None, default_platform: str = None, terms_to_accept: str = None,
                 enforce_terms_to_accept: bool = None):
        self._project_id = project_id
        self._description = description
        self._display_name = display_name
        self._resource_prefix = resource_prefix
        self._project_group_id = project_group_id
        self._jfrog_repository_id = jfrog_repository_id
        self._onboard_email = onboard_email
        self._onboard_message = onboard_message
        self._environment = environment
        self._default_platform = default_platform
        self._terms_to_accept = terms_to_accept
        self._enforce_terms_to_accept = enforce_terms_to_accept

    @property
    def project_id(self):
        """
        Get Project_id

        @return project_id
        """
        return self._project_id

    @property
    def default_platform(self):
        """
        Get default_platform

        @return default_platform
        """
        return self._default_platform

    @property
    def description(self):
        """
        Get description

        @return description
        """
        return self._description

    def set_description(self, description):
        """
        set description.
        @param description

        @return new value of description
        """
        self._description = description

    @property
    def display_name(self):
        """
        Get display_name

        @return display_name
        """
        return self._display_name

    def set_display_name(self, display_name):
        """
        set display_name
        @param display_name

        @return new value of display_name
        """
        self._display_name = display_name

    @property
    def resource_prefix(self):
        """
        Get resource prefix

        @return resource prefix
        """
        return self._resource_prefix

    @property
    def project_group_id(self):
        """
        Get Project group id.

        @return project group id.
        """
        return self._project_group_id

    @property
    def jfrog_repository_id(self):
        """
        Get jfrog repository id

        @return jfrog repository id.
        """
        return self._jfrog_repository_id

    @property
    def onboard_email(self):
        """
        Get onboard email.

        return oboard email
        """
        return self._onboard_email

    @property
    def onboard_message(self):
        """
        Get onboard message.

        @return onboard message.
        """
        return self._onboard_message

    @property
    def environment(self):
        """
        Get environment

        @return environment.
        """
        return self._environment

    @environment.setter
    def environment(self, value):
        """
        Set environment.
        @param: value

        @return new value of environment.
        """
        self._environment = value

    @property
    def terms_to_accept(self) -> str:
        """
        Get terms_to_accept

        @return terms_to_accept.
        """
        return self._terms_to_accept

    @property
    def enforce_terms_to_accept(self) -> bool:
        """
        Get enforce_terms_to_accept

        @return enforce_terms_to_accept.
        """
        return self._enforce_terms_to_accept

    def to_json_dict(self):
        """
        return json dict
        """
        return {
            "projectId": self.project_id,
            "description": self.description,
            "displayName": self.display_name,
            "resourcePrefix": self.resource_prefix,
            "projectGroupId": self.project_group_id,
            "jFrogRepositoryId": self.jfrog_repository_id,
            "onboardEmail": self.onboard_email,
            "onboardMessage": self.onboard_message,
            "environment": self.environment,
            "defaultPlatform": self.default_platform,
            "termsToAccept": self.terms_to_accept,
            "enforceTermsToAccept": self.enforce_terms_to_accept
        }

    def to_metadb_object(self):
        """
        Convert to metadb related objects

        @return: project general properties
        """
        # Exclude 'description' and 'displayName' keys as we pick these from subjects.
        db_project_settings = {key: value for key, value
                               in EntityProjectGeneralSettings.to_json_dict(self).items()
                               if key not in ['description', 'displayName', 'projectId']}
        return ProjectProperties(PROJECT_ID=self.project_id,
                                 PROPERTIES=db_project_settings)

    @staticmethod
    def from_metadb_object(db_object: ProjectProperties):
        """
        Convert db object to entity object
        """
        if db_object is None:
            return None
        properties = db_object.PROPERTIES
        return EntityProjectGeneralSettings(project_id=db_object.PROJECT_ID,
                                            resource_prefix=properties.get('resourcePrefix',
                                                                           'data_ingest_{{dataset_name}'),
                                            project_group_id=properties.get('projectGroupId'),
                                            jfrog_repository_id=properties.get('jFrogRepositoryId'),
                                            onboard_email=properties.get('onboardEmail'),
                                            onboard_message=properties.get('onboardMessage'),
                                            environment=properties.get('environment', 'dev'),
                                            default_platform=properties.get('defaultPlatform', 'glue'),
                                            enforce_terms_to_accept=properties.get('enforceTermsToAccept', False),
                                            terms_to_accept=properties.get(
                                                'termsToAccept', "<p>Terms were not yet defined in the settings</p>")
                                            )

    @staticmethod
    def from_metadb_objects(db_objects: list):
        """
        Convert list of db objects to list of  entity objects
        """
        if not db_objects:
            return []
        result = []
        for db_object in db_objects:
            result.append(EntityProjectGeneralSettings.from_metadb_object(db_object))
        return result

    @staticmethod
    def from_json_dict(project_id, json_dict):
        """
        create project general settings  from request information

        """
        return EntityProjectGeneralSettings(
            project_id=project_id,
            description=json_dict.get('description'),
            display_name=json_dict.get('displayName'),
            resource_prefix=json_dict.get('resourcePrefix', 'data_ingest_{{dataset_name}'),
            project_group_id=json_dict.get('projectGroupId'),
            jfrog_repository_id=json_dict.get('jFrogRepositoryId'),
            onboard_email=json_dict.get('onboardEmail'),
            onboard_message=json_dict.get('onboardMessage'),
            environment=json_dict.get('environment', 'dev'),
            default_platform=json_dict.get('defaultPlatform', 'glue'),
            enforce_terms_to_accept=json_dict.get("enforceTermsToAccept", False),
            terms_to_accept=json_dict.get("termsToAccept")
        )
