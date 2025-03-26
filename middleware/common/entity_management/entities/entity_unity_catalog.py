from middleware.common.entity_management.entities.entity_object import EntityObject
from middleware.common.entity_management.entities.entity_unity_schema import EntityUnitySchema


class EntityUnityCatalog(EntityObject):
    """
    Entity unity catalog
    """

    def __init__(self, name=None, permissions=None, unity_schemas: {EntityUnitySchema} = {}):
        self._name = name
        self._permissions = permissions
        self._unity_schemas = unity_schemas

    @property
    def name(self):
        """
        get name

        return name
        """
        if self._name is None:
            return None
        return self._name

    def set_name(self, name):
        """
        set name

        :param name: new value of name
        """
        self._name = name

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

        :param permissions: new value of permissions
        """
        self._permissions = permissions

    @property
    def unity_schemas(self):
        """
        get unity_schemas

        return unity_schemas
        """
        if self._unity_schemas is None:
            return None
        return self._unity_schemas

    def set_unity_schemas(self, unity_schemas):
        """
        set unity_schemas

        :param unity_schemas: new value of unity_schemas
        """
        self._unity_schemas = unity_schemas

    def to_json_dict(self):
        """
        Return a JSON representation of entity unity catalog
        """
        dict_unity_schemas = {}
        if self.unity_schemas:
            for name, unity_schema in self.unity_schemas.items():
                dict_unity_schemas[name] = unity_schema.to_json_dict()

        json_dict = {
            "name": self.name,
            # "permissions": self.permissions,
            "unity_schemas": dict_unity_schemas
        }
        if self.permissions:
            json_dict["permissions"] = self.permissions
        return json_dict

    @staticmethod
    def from_json_dict(unity_catalog: dict):
        """
        Return instance of EntityUnityCatalog created from json dict

        :param unity_catalog: dict representation of unity_catalog
        """
        unity_schemas = {}
        for key, value in unity_catalog["unity_schemas"].items():
            unity_schemas[key] = EntityUnitySchema.from_json_dict(value)
        return EntityUnityCatalog(
            name=unity_catalog.get("name", None),
            permissions=unity_catalog.get("permissions", None),
            unity_schemas=unity_schemas
        )