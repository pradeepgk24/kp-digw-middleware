from middleware.common.entity_management.entities.entity_object import EntityObject


class EntityUnitySchema(EntityObject):
    """
    Entity unity schema
    """

    def __init__(self, skip_creation: bool = False, schema_name: str = None, s3_layer_path: str = None,
                 permissions=None):
        self._skip_creation = skip_creation
        self._schema_name = schema_name
        self._s3_layer_path = s3_layer_path
        self._permissions = permissions

    @property
    def skip_creation(self):
        """
        get skip_creation

        return skip_creation
        """
        if self._skip_creation is None:
            return None
        return self._skip_creation

    def set_skip_creation(self, new_skip_schema):
        """
        get skip_creation

        return skip_creation
        """
        self._skip_creation = new_skip_schema

    @property
    def schema_name(self):
        """
        get schema_name

        return schema_name
        """
        if self._schema_name is None:
            return None
        return self._schema_name

    def set_schema_name(self, schema_name):
        """
        set schema_name

        return schema_name
        """
        self._schema_name = schema_name

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

        return s3_layer_path
        """
        self._s3_layer_path = s3_layer_path

    @property
    def permissions(self):
        """
        get permissions

        return permissions
        """
        if self._permissions is None:
            return None
        return self._permissions

    def set_permissions(self, permissions):
        """
        set permissions

        return permissions
        """
        self._permissions = permissions

    def to_json_dict(self):
        """
        Return a JSON representation of entity schema
        """
        json_dict = {
            "skip_creation": self.skip_creation,
            "schema_name": self.schema_name
        }
        if self.s3_layer_path:
            json_dict["s3_layer_path"] = self.s3_layer_path
        if self.permissions:
            json_dict["permissions"] = self.permissions
        return json_dict

    @staticmethod
    def from_json_dict(dict_schema: dict):
        """
        Return instance of EntityUnitySchema created from json dict

        :param dict_schema: dict representation of entity unity schema
        """
        return EntityUnitySchema(
            skip_creation=dict_schema.get("skip_creation", False),
            schema_name=dict_schema.get("schema_name"),
            s3_layer_path=dict_schema.get("s3_layer_path"),
            permissions=dict_schema.get("permissions")
        )


