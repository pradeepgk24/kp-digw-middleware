from middleware.common.metadatabase.clients.meta_database_client import MetaDatabaseClient
from middleware.common.metadatabase.model.difw_metadb_model import ProjectProperties, SubjectsHierarchy


class InfrastructureMetadataProvider(MetaDatabaseClient):
    """
    Database client which served actions related with Infrastructure
    """

    def get_project_onboard_and_groups_information(self) -> list:
        """
        Call which obtains both all possible projects, theirs onboard information and underlying groups
        As this call does not undergo any validation
        We use with_entities, to return only the information we need
        The groups are joined onto the projectProperties table  - with this we return more entries, however because of
        it we can do it in one call only
        @return: list of all entries - tuples of three
        """
        # join ProjectProperties with SubjectsHierarchy to get all underlying groups
        dynamic_query = self.session.query(ProjectProperties).\
            join(SubjectsHierarchy, ProjectProperties.PROJECT_ID == SubjectsHierarchy.PARENT_ID)
        # use with_entities to return only the necessary info
        dynamic_query = dynamic_query.with_entities(ProjectProperties.PROJECT_ID, ProjectProperties.PROPERTIES,
                                                    SubjectsHierarchy.CHILD_ID)
        return dynamic_query.all()
