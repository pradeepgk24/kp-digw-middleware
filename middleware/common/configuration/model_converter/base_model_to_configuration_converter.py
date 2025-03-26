from abc import abstractmethod
from typing import Any

from middleware.common.configuration.model_converter.config_model_converter import ConfigModelConverter
from middleware.common.configuration.model_converter.resolvers.config_resolver import ConfigPartResolver
from middleware.common.entity_management.entities.entity_object import EntityObject
from middleware.common.entity_management.secrets_management import SecretsManagement


class BaseModelToConfigurationConverter(ConfigModelConverter):
    """
    Abstract class for model to configuration converter
    """

    def __init__(self, logger, secrets_management: SecretsManagement):
        super().__init__(logger, secrets_management)
        self.platform = None
        self.context = dict()
        self.final_configuration = dict()
        self.resolvers = None

    def add_context_property(self, property_name: str, property_value: Any):
        """
        Add new property into context

        @param property_name: name of property
        @param property_value: value of property
        """
        self.context[property_name] = property_value

    def get_context_property(self, property_name: str, default_value: Any = None) -> Any:
        """
        Get property from context

        @param property_name: name of property
        @param default_value: default value in case there is no property with the specific name in context

        @return: value of property
        """
        if property_name in self.context:
            return self.context[property_name]
        return default_value

    def convert_model_to_yaml_config(self, input_entity: EntityObject, **kwargs):
        """
        Method go resolver by resolver and compose final configuration

        @param input_entity: Input entity to convert
        @param kwargs: additional arguments
        """
        # check if kwargs contains all parameters needed for next steps within resolvers,
        if not all(parameter_name in kwargs for parameter_name in self.get_mandatory_input_parameters()):
            raise Exception(f"For method convert_model_to_yaml_config missing one of the parameter "
                            f"{self.get_mandatory_input_parameters()}")
        # save main entity into contex, so it can be referenced in other steps
        self.add_context_property("input_entity", input_entity)
        for resolver_class in self.get_config_part_converters():
            self.logger.info(f"Going to start config part resolver {resolver_class.__class__.__name__}")
            resolver = resolver_class(self)
            config_key_path, config_part = resolver.resolve_model_to_config(input_entity, **kwargs)
            config_to_enhance = self.final_configuration
            if config_key_path and config_part:
                # key is defined, therefore find proper key where the configuration should be put
                for inner_key in config_key_path.split('/'):
                    # if the key is not yet present, add it there
                    if inner_key not in config_to_enhance:
                        if inner_key.endswith("[:]"):
                            inner_key = inner_key.replace("[:]", "")
                            config_to_enhance[inner_key] = []
                        else:
                            config_to_enhance[inner_key] = {}
                    config_to_enhance = config_to_enhance[inner_key]
            if config_part:
                if isinstance(config_to_enhance, list):
                    # in case it is dict only a key was written through via extend
                    if isinstance(config_part, dict):
                        config_to_enhance.extend(config_part.items())
                    else:
                        config_to_enhance.extend(config_part)
                else:
                    config_to_enhance.update(config_part)
        return self.final_configuration

    @abstractmethod
    def get_config_part_converters(self) -> [ConfigPartResolver.__class__]:
        """
        Abs method to get configuration part converters
        """

    @abstractmethod
    def get_mandatory_input_parameters(self) -> [str]:
        """
        Abs method to list of mandatory parameters to method convert_model_to_yaml_config
        """
