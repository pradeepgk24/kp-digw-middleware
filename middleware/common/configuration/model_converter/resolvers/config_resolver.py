import collections
from abc import abstractmethod, ABC

from common.secrets.secrets import SecretValue
from middleware.common.entity_management.entities.entity_object import EntityObject
from middleware.common.helpers.utils import convert_str_dict_to_correct_types


class ConfigPartResolver(ABC):
    """
    Each part of configuration is resolved in some way. Each config part is resolve independently
    If there is any need to work with result from other resolver the context from converter can be used
    """

    def __init__(self, converter):
        self.converter = converter

    @abstractmethod
    def resolve_model_to_config(self, input_entity: EntityObject, **kwargs) -> (str, dict):
        """
        Abstract method to convert one part of model configuration to one part of yaml configuration.
        @param input_entity:  input entity
        @param kwargs:  additional parameters
        @return:
            As a result is pair
                - first element = key in final configuration where resolved configuration should put.
                In case it is empty, the config part will be saved into root of final configuration
                In this case there is slash (for example `key1/key2`) then the resolved configuration will be store as
                inner element key1/key2 of final configuration. If key ends with [:] then it means it is list
                for example key1Dict/Key2List[:]
                - second element = configuration part as dict
        """
        pass

    @staticmethod
    def _is_attr_empty(value):
        """
        check if value is empty

        @param value: value to check
        @return: flag indicates if value is empty or not
        """
        if value is None:
            return True
        if isinstance(value, collections.abc.Sized) and len(value) == 0:
            return True
        return False

    @staticmethod
    def map_object_attr_to_dict(input_entity: EntityObject, attr_path: [str], output_dict: dict, dict_path: [str],
                                default_value=None, mapping_allowed: bool = True, conversion_function=None):
        """
        Take value from input_entity represented by attr path and store it into output_dict into path
        represented by parameter dict_path


        @param input_entity: input entity
        @param attr_path: attr_path
        @param output_dict: output_dict
        @param dict_path: dict_path
        @param default_value: default_value
        @param mapping_allowed: flag indicates if mapping is needed
        @param conversion_function: conversion function
        """
        # skip all if mapping is not allowed
        if not mapping_allowed:
            return
            # get the value from input entity
        input_entity_attr_value = input_entity
        for attr_name in attr_path:
            if hasattr(input_entity_attr_value, attr_name):
                input_entity_attr_value = getattr(input_entity_attr_value, attr_name)
                if input_entity_attr_value is None:
                    break
            else:
                input_entity_attr_value = None

        # put default value if the attr value is not defined
        if ConfigPartResolver._is_attr_empty(input_entity_attr_value):
            input_entity_attr_value = default_value

        # assign the value to output dictionary only in case there is any value to assign
        if not ConfigPartResolver._is_attr_empty(input_entity_attr_value):
            # run conversion function if needed
            if conversion_function:
                input_entity_attr_value = conversion_function(input_entity_attr_value)
            config_to_update = output_dict
            final_key = dict_path.pop()
            for inner_key in dict_path:
                # if the key is not yet present, add it there
                if inner_key not in config_to_update:
                    config_to_update[inner_key] = {}
                config_to_update = config_to_update[inner_key]
            config_to_update[final_key] = input_entity_attr_value

    @staticmethod
    def map_object_attr_to_dict_bulk(input_entity: EntityObject, output_dict: dict, mapping_pair: []):
        """
        Bulk call of method map_object_attr_to_dict

        @param input_entity:  input entity
        @param output_dict:  output_dict
        @param mapping_pair:  mapping_pair
        """
        for map_item in mapping_pair:
            attr_path = map_item[0]
            dict_path = map_item[1]
            default_value = None
            if len(map_item) > 2:
                default_value = map_item[2]
            mapping_allowed = True
            if len(map_item) > 3:
                mapping_allowed = map_item[3]
            conversion_function = None
            if len(map_item) > 4:
                conversion_function = map_item[4]
            ConfigPartResolver.map_object_attr_to_dict(input_entity, attr_path, output_dict, dict_path,
                                                       default_value, mapping_allowed, conversion_function)

    @staticmethod
    def _create_sql_spark_configuration_section(sql_config_dict):
        """
        Create dict representation of spark config section -> jobs/<job>/spark_config from model.
        @param sql_config_dict:
        @return: list of SQL configuration
        """
        spark_sql_config_section = []
        if sql_config_dict:
            for sql_config_key, sql_config_value in sql_config_dict.items():
                spark_sql_config_section.append(f"set {sql_config_key}={sql_config_value}")
        return spark_sql_config_section

    def _resolve_secret_manager_name(self, secret_attr_value: dict):
        """
        Resolve secret manager name based on secret

        @param secret_attr_value: value of secret contains 2 keys secretManagerName  and secretName
        @return: name of AWS SM
        """
        aws_sm_name = secret_attr_value.get("secretManagerName")
        secret_name = secret_attr_value.get("secretName")
        if not aws_sm_name:
            secret = self.converter.secrets_management.get_secret(secret_name, False, False, False)
            if secret:
                aws_sm_name = secret.secret_manager_name
            else:
                self.converter.logger.warning(f"Secret with name {secret_name} does not exists.")
        return aws_sm_name

    def _get_attr_value_from_dynamic_attribute(self, model_attr):
        """
        Get attr value from model attribute

        @param model_attr:
        @return: value of model attr
        """

        object_type = model_attr["type"]["objectType"].lower()
        attribute_value = None
        if not model_attr["type"].get("isInUse", True):
            return None
        if object_type == self.converter.MODEL_TYPE_DICTIONARY:
            attribute_value = convert_str_dict_to_correct_types(model_attr.get("value"))
        elif self._is_attr_basic_model_type(object_type):
            attribute_value = model_attr.get("value")
        elif object_type == self.converter.MODEL_TYPE_SECRET:
            attribute_value = None
            secret_value = model_attr.get("value", {})
            if secret_value:
                secret_manager_name = secret_value.get("secretManagerName")
                if not secret_manager_name:
                    secret_manager_name = self._resolve_secret_manager_name(secret_value)
                attribute_value = SecretValue(secret_manager_name, secret_value["secretKey"])
        elif object_type == self.converter.MODEL_TYPE_OBJECT:
            attribute_value = self._convert_dynamic_attributes_to_simple_dict(
                model_attr["type"].get("attributes", []))
        elif object_type == self.converter.MODEL_TYPE_LIST:
            if self._is_attr_basic_model_type(model_attr["type"]["elementsType"]["objectType"].lower()):
                attribute_value = model_attr.get("value")
            elif model_attr["type"]["elementsType"]["objectType"].lower() in self.converter.MODEL_TYPE_OBJECT:
                attribute_value = []
                for attr_value in model_attr.get("value", []):
                    attribute_value.append(self._convert_dynamic_attributes_to_simple_dict(attr_value["attributes"]))
        else:
            raise Exception(
                f"Not specific object type {object_type} for attribute '{model_attr['attributeName']}'")
        return attribute_value

    def _convert_dynamic_attributes_to_simple_dict(self, attributes: list) -> dict:
        """
        Convert dynamic attributes to simple dictionary

        @param attributes:
        @return:
        """
        dataset_config_result = dict()
        for model_attr in attributes:
            attribute_value = self._get_attr_value_from_dynamic_attribute(model_attr)
            # assign value if there is any attr value defined or if there is direct false value defined
            # sample not acceptable values attribute_value: None , attribute_value: [], attribute_value: {}
            if attribute_value is False or attribute_value:
                # if there is dynamicPattern in value, it means that it is object with dynamic attribute names
                # therefore take resolved attribute_value (what is list) and assign particular items into
                # the dataset_config_result instead of assigning the attribute_value directly. It will cause, that
                # meta attribute name which only have info about dynamicPattern is skipped and will not be part of final
                # yaml configuration
                if "dynamicPattern" in model_attr['type']:
                    for attr_name, value_of_dynamic_attr in attribute_value.items():
                        dataset_config_result[attr_name] = value_of_dynamic_attr
                else:
                    dataset_config_result[model_attr["attributeName"]] = attribute_value
        return dataset_config_result

    def _is_attr_basic_model_type(self, attribute_type):
        """
        Check is attr type is basic model type

        @param attribute_type:
        @return:
        """
        return attribute_type in self.converter.BASIC_MODEL_TYPES
