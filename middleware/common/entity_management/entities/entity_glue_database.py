from middleware.common.entity_management.entities.entity_object import EntityObject


class EntityGlueDatabase(EntityObject):
    """
    Entity glue database catalog
    """

    def __init__(self, database_name: str = None, s3_layer_path: str = None):
        self._database_name = database_name
        self._s3_layer_path = s3_layer_path

    @property
    def database_name(self):
        """
        get database_name

        return database_name
        """
        if self._database_name is None:
            return None
        return self._database_name

    def set_database_name(self, database_name):
        """
        set database_name

        :param database_name: new value of database_name
        """
        self._database_name = database_name

    @property
    def s3_layer_path(self):
        """
        get s3_layer_path

        return s3_layer_path
        """
        if self._s3_layer_path is None:
            return None
        return self._s3_layer_path

    def set_s3_layer_path(self, s3_layer_path):
        """
        set s3_layer_path

        :param s3_layer_path: new value of s3_layer_path
        """
        self._s3_layer_path = s3_layer_path

    def to_json_dict(self):
        """
        Return a JSON representation of entity glue database
        """
        json_dict = {
            "database_name": self.database_name,
            "s3_layer_path": self.s3_layer_path
        }
        return json_dict

    @staticmethod
    def from_json_dict(dict_glue_database: dict):
        """
        Return instance of EntityGlueDatabase created from json dict

        :param dict_glue_database: dict representation of entity glue database
        """
        return EntityGlueDatabase(
            database_name=dict_glue_database.get("database_name"),
            s3_layer_path=dict_glue_database.get("s3_layer_path")
        )