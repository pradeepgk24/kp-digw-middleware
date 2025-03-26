import json
import os
from typing import TypeVar
import yaml
from middleware.api.common.event_utils import DIFWAPIGatewayProxyEvent
from middleware.common.helpers.exception import BadRequest
from common.secrets.secrets_manger import SecretsManager


def get_env_or_header_value(event: DIFWAPIGatewayProxyEvent, env_name: str, header_name: str, logger) -> str:
    """
    Get the value of the environment variable , if not present then get the header value from the event.headers

    @param event: the Api Gateway ProxyEvent
    @param env_name: the name of the environment variable
    @param header_name: the name of the http header
    @param logger: the logger instance

    @return: the value of the environment variable or the http header
    @rtype: string
    """
    if os.environ.get(env_name):
        logger.info(f"Going to use os environment {env_name}")
        return os.environ[env_name]
    logger.info(f"Going to use event header with name {header_name}")
    if event.headers.get(header_name):
        return event.headers.get(header_name)

    raise BadRequest(f"No os env {env_name} or {header_name} header set")


# pylint: disable=expression-not-assigned
def is_valid_yaml_or_json(cluster_options, cluster_options_format):
    """
    Validates the format of cluster options provided as input.

    This function checks whether the given cluster options are valid JSON or YAML
    based on the requested format.

    If the requested format is JSON:
        - It will attempt to parse the `clusterOptions` as JSON.
        - If parsing fails, a BadRequest exception is raise.

    If the requested format is YAML:
        - The function first checks if the `clusterOptions` can be parsed as JSON.
        - If it can, a BadRequest exception is raised indicating that JSON was passed when YAML was expected.
        - If it cannot be parsed as JSON, the function then attempts to parse it as YAML.
        - If the YAML parsing fails, a BadRequest exception is raised.


    @param cluster_options: can be JSON or JSON string containing options for the cluster.
    @param cluster_options_format: The format of the cluster options as a string.

    """
    if cluster_options_format not in ("JSON", "YAML"):
        raise BadRequest(
            "Bad input type for cluster options format.Supported types are YAML and JSON.")
    try:
        # The below line of code checks the following:
        # 1. json.loads will be performed if the cluster options are of type string.
        #    This occurs when the user selects a cluster options format as YAML but passes JSON cluster options.
        # 2. When the user selects the cluster options format as JSON and passes cluster options that are
        # valid JSON by default running json.loads will produce an error, json.dumps is used to ensure the input
        #  is in the correct format before attempting json.loads again.

        json.loads(cluster_options) if isinstance(cluster_options, str) else json.loads(json.dumps(cluster_options))

        if cluster_options_format == "YAML":
            raise BadRequest("JSON cluster options passed instead of YAML.")
    except json.JSONDecodeError as ex:
        if cluster_options_format == "JSON":
            raise BadRequest("Invalid JSON passed for cluster options of type JSON.Please check") from ex
    try:
        # If it's not JSON, check if it's valid YAML
        if cluster_options_format == "YAML":
            yaml.safe_load(cluster_options)
    except yaml.YAMLError as ex:
        # raise an error if there are any issues while parsing the yaml also catches yaml.parser.ParserError
        raise BadRequest("Invalid YAML passed for cluster options of type YAML.Please check") from ex


def validate_dictionary(keys, model):
    """
    Validate if the given keys are present in the model.

    :param keys:
    :param model:
    :return list of keys that are not present in the model
    """
    not_valid_keys = []
    for key in keys:
        if key not in model:
            not_valid_keys.append(key)
    return not_valid_keys


class SortAndPaginate:
    """
    Class, which provides sorting and pagination properties, also provides helper function for relisting stringed list
    from request
    """

    def __init__(self, dict_in: dict):
        self.sorted_conversion, self.page_size, self.page_number = self.variables_from_request(dict_in)

    def variables_from_request(self, query_parameters: dict):
        """
        Helper function, which cleans and return request query parameters
        :param query_parameters:
        """
        sorted_conv = self.find_sort_entries_in_dict(
            self.clean_and_relist_listed_strings(query_parameters.get('sort')))
        page_size = int(query_parameters.get('pageSize', 15))
        page_number = int(query_parameters.get('pageNumber', 1))
        return sorted_conv, page_size, page_number

    @staticmethod
    def clean_and_relist_listed_strings(stringed_list: str):
        """
        Helper function, which cleans and return request query parameters
        :param stringed_list:
        """
        return None if stringed_list in (None, '') else [item.strip() for item in stringed_list.strip('][').split(',')]

    @staticmethod
    def find_sort_entries_in_dict(sort: list = None):
        """
        As the sorting can be done in DB level, the sorting names there are different, so we need to
        interchange the names in request with appropriate version. As there are only few options, we can do it
        via dictionary.
        :param sort:
        :return sort_conversion:
        """
        if sort is None:
            return None
        conversion_dictionary = {"templateName": "COMPONENT_NAME", "componentTypeName": "COMPONENT_TYPE_NAME",
                                 "componentCategory": "COMPONENT_TYPE_CATEGORY", "difwCoreVersion": "DIFW_CORE_VERSION",
                                 "pipelineTemplateName": "OBJECT_FULL_NAME", "pipelineName": "OBJECT_FULL_NAME",
                                 "workflowName": "OBJECT_FULL_NAME",
                                 "isEnabled": "IS_ENABLED", "secretName": "SECRET_NAME",
                                 "permissionName": "PERMISSION_NAME", "displayName": "DISPLAY_NAME",
                                 "isDraft": "IS_DRAFT"}
        sort_conversion = []
        for key_sort in sort:
            ascending_sort = not key_sort.startswith('-')
            key_to_sort_by = key_sort.lstrip('+- ')
            # as isEnabled in only boolean sorting option, where we would not prefer false before true (0->1)
            if key_to_sort_by == "isEnabled":
                ascending_sort = not ascending_sort
            sort_conversion.append({"sort_key": conversion_dictionary.get(key_to_sort_by),
                                    "ascending_order": ascending_sort})
        return sort_conversion


T = TypeVar("T")
def paginate_entries(entries_list: list[T] = None, sort_and_paginate: SortAndPaginate = None) -> list[T]:
    """
    Helper function to process pagination of given list,
    most of the filtering should happen in DB via offset+limit, however in some scenarios (eg. get_secrets method)
    it is possible, that additional filtering will happen and then the pagination done in DB would not be valid.
    Keep in mind, we are indexing in list
    :param entries_list:
    :param sort_and_paginate:
    :param sort_and_paginate:
    """
    if not entries_list:
        return []
    if sort_and_paginate is None:
        return entries_list
    offset_in_list = (sort_and_paginate.page_number - 1) * sort_and_paginate.page_size
    return entries_list[offset_in_list:(offset_in_list + sort_and_paginate.page_size)]


# TODO https://issues.merck.com/browse/NGA-3751 enhance sorting for Owner column in UI
def add_order_to_query(query, object_table, sorting_info_list: list):
    """
    Function which adds to sql_alchemy query order_by statements based on sorting_info_list,
    function is called in corresponding metadata_provider classes
    :param query: sql_alchemy query
    :param object_table: object - table
    :param sorting_info_list: list of sorting arguments
    """
    for sorting_info in sorting_info_list:
        query = query.order_by(getattr(object_table, sorting_info.get("sort_key")).asc() if
                               sorting_info.get("ascending_order")
                               else getattr(object_table, sorting_info.get("sort_key")).desc())

    return query


def convert_to_bool(value):
    """
    Convert the String or Int value to Bool

    :param value:
    :return: true/false or None if value is None
    """
    if value is None:
        return None
    if str(value).lower() in ['true', '1', 't']:
        return True
    return False


def set_redis_key(token_info: dict, redis_client):
    """
    Set the redis key for the token_info dictionary using the redis.set method of the redis_client class

    @param token_info: dictionary with the token information which needs to be converted to json prior
    to setting the key in redis
    @param redis_client: the redis client
    @return: result
    """
    redis_key = token_info['access_token']
    expire = token_info['expires_in']
    redis_val = json.dumps(token_info)
    return redis_client.set(redis_key, redis_val, ex=expire)


def get_redis_key(key: str, redis_client):
    """
    Get the value of the given key from Redis

    @param key: the key to retrieve the value for
    @param redis_client: the redis client
    @return: the value of the key
    """
    redis_val = redis_client.get(key)
    if redis_val is None:
        return None
    return json.loads(redis_val)


def delete_redis_key(key: str, redis_client):
    """
    Delete the key key from the Redis using redis_client

    @param key: the key to delete from the Redis
    @param redis_client: the redis client
    """
    return redis_client.delete(key)


def get_middleware_logging_level() -> str:
    """
    Get the logging level from the environment variable MIDDLEWARE_LOGGING_LEVEL, defaults to `INFO`

    @return: the logging level for the middleware
    """
    return os.environ.get('MIDDLEWARE_LOGGING_LEVEL', 'INFO')


def get_lambda_secrets_manager() -> SecretsManager:
    """
    Get the region aws secrets manager that store credentials to other essential services

    @return: aws secrets manager
    """
    runtime_region = os.environ.get('AWS_REGION', default="us-east-1")
    return SecretsManager(runtime_region)