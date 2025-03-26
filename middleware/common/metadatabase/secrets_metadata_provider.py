from sqlalchemy import and_, func

from middleware.api.common.helpers import SortAndPaginate, add_order_to_query
from middleware.common.metadatabase.clients.meta_database_client import MetaDatabaseClient
from middleware.common.metadatabase.model.difw_metadb_model import Secrets, SecretsACL, Subjects


class SecretsMetadataProvider(MetaDatabaseClient):
    """
    Database client which served actions related with secrets
    """

    def insert_or_update_secret(self, secret: Secrets, user_id: str):
        """
        Insert or update secret

        :param secret: secret which will be either created or updated
        :param user_id: user who create/update the secret

        :return: inserted or updated secret
        """
        return self.insert_or_update_record(secret, user_id)

    def insert_secret(self, secret: Secrets, user_id: str):
        """
        Creates secrets in MetaDB.

        :param secret:
        :param user_id:
        :return:
        """
        return self.insert_record(secret, user_id)

    def update_secret(self, secret: Secrets, user_id):
        """
        Update existing secret

        :param secret:
        :param user_id: user who update the secret
        :return: updated secret
        """
        return self.update_record(secret, user_id)

    def delete_secret(self, secret: Secrets, user_id: str):
        """
        Delete secret

        :param secret: secret to delete
        :param user_id: logon user isid
        """
        self.delete_record(secret, user_id)

    def delete_secret_acl(self, secret: SecretsACL, user_id: str):
        """
        Delete secret

        :param secret: secret to delete
        :param user_id: logon user isid
        """
        self.delete_record(secret, user_id)

    def get_secrets(self, user_id: str, project_id: str, secret_name: str = None,
                    sort_and_paginate: SortAndPaginate = None):
        """
        Gets all secret details for current project from Metadata DB.

        :param user_id: logon user isid
        :param project_id:
        :param secret_name: optional, possible filtering upon substring
        :param sort_and_paginate:
        :return:
        """
        # we get all secrets, which we don't want
        dynamic_query = self.session.query(Secrets). \
            join(SecretsACL, Secrets.SECRET_NAME == SecretsACL.SECRET_NAME). \
            join(Subjects, and_(SecretsACL.SUBJECT_ID == Subjects.SUBJECT_ID,
                                SecretsACL.SUBJECT_ID == project_id))
        if secret_name:
            dynamic_query = dynamic_query.filter(Secrets.SECRET_NAME.ilike(f"%{secret_name}%"))
        self.logger.info(f"User {user_id} going to get all secret details for project in {project_id}")
        if sort_and_paginate and sort_and_paginate.sorted_conversion:
            dynamic_query = add_order_to_query(dynamic_query, Secrets, sort_and_paginate.sorted_conversion)

        return dynamic_query.all()

    def get_secret(self, secret_name: str, user_id: str):
        """
        Get secret from DB

        :param user_id:
        :param secret_name:

        :return: secret
        """
        self.logger.info(f"User {user_id} is going to retrieve secret with name {secret_name} ")
        return Secrets(SECRET_NAME=secret_name).get_unique(self.session)

    def get_secret_by_sm_name(self, secret_manager_name: str, user_id: str):
        """
        Get secret from DB

        :param user_id:
        :param secret_manager_name:

        :return: secret
        """
        self.logger.info(
            f"User {user_id} is going to retrieve secret where secret manager name = {secret_manager_name}")
        return Secrets.get_many(self.session, and_(Secrets.SECRET_MANAGER_NAME == secret_manager_name))

    # pylint: disable=not-callable
    def exists_secret(self, secret_name, user_id: str = "") -> bool:
        """
        Check if secret with the specific name exists

        :param secret_name:
        :param user_id:

        :return: flag indicates if secret either exists or not
        """
        self.logger.info(f"User {user_id} is going to check if secret with name {secret_name} exists")

        secret_count = self.session.query(func.count(Secrets.SECRET_NAME)).filter(Secrets.SECRET_NAME == secret_name) \
            .scalar()
        return secret_count > 0