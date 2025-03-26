from abc import ABCMeta, abstractmethod
import json

from middleware.common.metadatabase.model.difw_metadb_model import ObjectProperties


class EntityObject(metaclass=ABCMeta):
    """
    Main metadata object for Entities
    """

    def __str__(self):
        """
        to string method
        :return:
        """
        return str(self.to_json_dict())

    @abstractmethod
    def to_json_dict(self):
        """
        Conversion object to dict which as a API response
        """

    @staticmethod
    def _convert_str_to_list(str_rep_of_list) -> list:
        """
        convert string to list
        :param str_rep_of_list: string representation of list

        :return: list
        """
        if not str_rep_of_list:
            return []
        return json.loads(str_rep_of_list.replace("'", '"').replace('None', ''))

    @staticmethod
    def convert_object_properties_to_entity_attributes(object_instance, data_mapping,
                                                       object_properties: [ObjectProperties]):
        """
        convert object properties to entity properties

        :param object_properties: list of object properties
        :param object_instance: target object instance
        :param data_mapping: list of mapping touples with following information
            index 0 - property name
            index 1 - column name, where the value is store. For example PROPERTY_STRING_VALUE
            index 2 - name of attribute from entity object
            index 3 - converting function to DB object
            index 4 - converting function to Entity object
            Item sample:
            ('table.staticPartitions', 'PROPERTY_STRING_VALUE', 'static_partitions', json.dumps, json.loads),
        """
        # map of property attribute and appropriate property value attribute
        obj_properties_dict_mapping = {mapping_item[2]: mapping_item for mapping_item in data_mapping}
        # map of property name and appropriate property object
        obj_properties_dict = {obj_property.PROPERTY_NAME: obj_property for obj_property in object_properties}

        for attribute_name, mapping_tuple in obj_properties_dict_mapping.items():
            # skip mapping if such property does not exists
            if mapping_tuple[0] not in obj_properties_dict:
                continue
            value_from_object_properties = getattr(obj_properties_dict[mapping_tuple[0]], mapping_tuple[1])
            set_function_of_object_instance = getattr(object_instance, f"set_{attribute_name}")
            if len(mapping_tuple) == 5:
                if value_from_object_properties is not None:
                    set_function_of_object_instance(mapping_tuple[4](value_from_object_properties))
            else:
                set_function_of_object_instance(value_from_object_properties)

    @staticmethod
    def convert_entity_attributes_to_object_properties(object_instance, data_mapping, object_full_name, object_version):
        """
        convert properties from entity to db object properties

        :param object_instance: source object instance
        :param data_mapping: list of mapping touples with following information
            index 0 - property name
            index 1 - column name, where the value is store. For example PROPERTY_STRING_VALUE
            index 2 - name of attribute from entity object
            index 3 - converting function to DB object
            index 4 - converting function to Entity object
            Item sample:
            ('table.staticPartitions', 'PROPERTY_STRING_VALUE', 'static_partitions', json.dumps, json.loads),
        :param object_full_name:
        :param object_version:

        """
        object_properties_list = []
        for mapping_item in data_mapping:
            # on index 3th there is callable function which need to be call before storing it into DB attribute
            object_instance_attr_value = getattr(object_instance, mapping_item[2])
            if isinstance(object_instance_attr_value, EntityObject):
                object_instance_attr_value = object_instance_attr_value.to_json_dict()

            object_properties_list.append(ObjectProperties(**{
                mapping_item[1]:
                    mapping_item[3](object_instance_attr_value) if
                    len(mapping_item) >= 4 and mapping_item[3] is not None and getattr(object_instance, mapping_item[2])
                    is not None else object_instance_attr_value,
                "PROPERTY_NAME": mapping_item[0],
                "OBJECT_FULL_NAME": object_full_name,
                "OBJECT_VERSION": object_version
            }))
        return object_properties_list

    @staticmethod
    def remove_keys(base_dictionary, keys_to_remove):
        """
        Clear the base directory by removing few keys to remove.

        @param base_dictionary
        @param keys_to_remove

        @return limited view of json dict
        """
        for key_to_remove in keys_to_remove:
            del base_dictionary[key_to_remove]
