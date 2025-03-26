import json

from middleware.common.entity_management.entities.entity_glue_database import EntityGlueDatabase
from middleware.common.entity_management.entities.entity_object import EntityObject
from middleware.common.entity_management.entities.entity_unity_catalog import EntityUnityCatalog


class EntityCatalogs(EntityObject):
    """
    Entity Catalogs for unity catalog and glue DB
    """

    def __init__(self, list_unity_catalog: [EntityUnityCatalog] = [],
                 dict_glue_databases: {} = {}):
        self._list_unity_catalog = list_unity_catalog
        self._dict_glue_databases = dict_glue_databases

    @property
    def list_unity_catalog(self):
        """
        get list_unity_catalog

        return list_unity_catalog
        """
        if self._list_unity_catalog is None:
            self._list_unity_catalog = [EntityUnityCatalog()]
        return self._list_unity_catalog

    def set_list_unity_catalog(self, list_unity_catalog):
        """
        set list_unity_catalog

        :param list_unity_catalog: new value of list_unity_catalog
        """
        self._list_unity_catalog = list_unity_catalog

    @property
    def dict_glue_databases(self):
        """
        get dict_glue_databases

        return dict_glue_databases
        """
        if self._dict_glue_databases is None:
            self._dict_glue_databases = {EntityGlueDatabase}
        return self._dict_glue_databases

    def set_dict_glue_databases(self, dict_glue_databases):
        """
        set dict_glue_databases

        :param dict_glue_databases: new value of dict_entity_glue_databases
        """
        self._dict_glue_databases = dict_glue_databases

    def to_json_dict(self):
        """
        Return a JSON representation of Entity Catalogs
        """
        if not self.list_unity_catalog and not self.dict_glue_databases:
            return {}
        list_unity_catalog_out = []
        dict_glue_databases_out = {}
        if self.list_unity_catalog:
            for unity_catalog in self.list_unity_catalog:
                list_unity_catalog_out.append(unity_catalog.to_json_dict())
        if self.dict_glue_databases:
            for name, glue_database in self.dict_glue_databases.items():
                dict_glue_databases_out[name] = glue_database.to_json_dict()
        return {
            "unityCatalog": list_unity_catalog_out,
            "glueDatabases": dict_glue_databases_out
        }

    @staticmethod
    def from_json_dict(catalogs: dict):
        """
        Return instance of EntityCatalogs created from json dict

        :param catalogs: dict representation of catalogs
        """
        if not catalogs:
            return {}
        list_unity_catalog = []
        dict_glue_databases = {}
        if "unityCatalog" in catalogs:
            for unity_catalog in catalogs["unityCatalog"]:
                list_unity_catalog.append(EntityUnityCatalog.from_json_dict(unity_catalog))
        if "glueDatabases" in catalogs:
            for name, glue_database in catalogs["glueDatabases"].items():
                dict_glue_databases[name] = EntityGlueDatabase.from_json_dict(glue_database)
        return EntityCatalogs(
            list_unity_catalog=list_unity_catalog,
            dict_glue_databases=dict_glue_databases
        )

    @staticmethod
    def from_str_dict(catalogs: str):
        """
        Return instance of EntityCatalogs created from str rep of json

        :param catalogs: str representation of catalogs
        """
        return EntityCatalogs.from_json_dict(json.loads(catalogs))

