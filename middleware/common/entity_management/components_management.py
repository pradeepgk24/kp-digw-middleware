import os
from io import StringIO

import boto3
import paramiko
import pysftp
import requests
from botocore.exceptions import ClientError
from oracledb import init_oracle_client
from paramiko.ssh_exception import SSHException
from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import DatabaseError
from urllib3.exceptions import NewConnectionError

from middleware.api.common.helpers import SortAndPaginate
from middleware.common.entity_management.entities.entity_component_type import EntityComponentType
from middleware.common.entity_management.entity_management import EntityManagement
from middleware.common.entity_management.project_settings_management import ProjectSettingsManagement
from middleware.common.entity_management.secrets_management import SecretsManagement
from middleware.common.helpers.exception import NoDataError, BadRequest, FailedConnectionError
from middleware.common.metadatabase.definitions_metadata_provider import DefinitionsMetadataProvider
from middleware.common.metadatabase.model.types.component_type_categories_enum import ComponentTypeCategoriesEnum


# pylint: disable=too-many-locals
class ComponentsManagement(EntityManagement):
    """
    Components management
    """

    # pylint: disable=duplicate-code
    # pylint: disable=too-many-arguments
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._definitions_metadata_provider = None
        self._secret_management = None
        self._project_settings_management = None
        self.refresh_aws_tokens(self.project_settings_management)

    @property
    def project_settings_management(self):
        """
        project settings management property
        """
        if self._project_settings_management is None:
            self._project_settings_management = ProjectSettingsManagement(
                logger=self.logger, metadatabase_connection=self.metadatabase_connection,
                lambda_secrets_manager=self.lambda_secrets_manager, user_isid=self.user_isid,
                selected_subjects=self.selected_subjects)
        return self._project_settings_management

    @property
    def secret_management(self):
        """
        secret_management property
        """
        if self._secret_management is None:
            self._secret_management = SecretsManagement(
                logger=self.logger, metadatabase_connection=self.metadatabase_connection,
                lambda_secrets_manager=self.lambda_secrets_manager, user_isid=self.user_isid,
                selected_subjects=self.selected_subjects, aws_access_key=self.aws_access_key,
                aws_secret_key=self.aws_secret_key, aws_session_token=self.aws_session_token)
        return self._secret_management

    @property
    def definitions_metadata_provider(self):
        """
        component_template_provider property
        """
        if self._definitions_metadata_provider is None:
            self._definitions_metadata_provider = DefinitionsMetadataProvider(
                self.logger, self.metadatabase_connection, self.lambda_secrets_manager)
        return self._definitions_metadata_provider

    # pylint: disable=inconsistent-return-statements
    def obtain_connector_objects(self, component_category: str, component_type_name: str, difw_core_version: str,
                                 request: dict, get_table_details: bool = False):
        """
        Obtain connector object

        :param component_category:
        :param component_type_name:
        :param difw_core_version:
        :param request:
        :param get_table_details:
        :return: list of
        """
        self.logger.info(f"Starting obtain_connector_objects method for component category {component_category}"
                         f" and type {component_type_name}.")
        component_type_entry = EntityComponentType.from_metadb_object(
            self.definitions_metadata_provider.get_component_type(
                self.user_isid, ComponentTypeCategoriesEnum.from_str(component_category),
                component_type_name, difw_core_version))
        if not component_type_entry:
            raise NoDataError(f"Component type with name {component_type_name}, component type category "
                              f"{component_category} and difw core version {difw_core_version} does not exist in DB")
        # extract information, create and connect from request
        if component_type_name == 'jdbc':
            # obtain chosen_object_type if it was passed in the request body
            chosen_objects_type_list = SortAndPaginate.clean_and_relist_listed_strings(
                request.get("additionalFiltering", {}).get("objectType", None))
            if chosen_objects_type_list and not set(chosen_objects_type_list) <= {"tables", "views",
                                                                                  "materializedViews"}:
                raise BadRequest(f"Selected objectType option {chosen_objects_type_list} is not of 'tables', 'views',"
                                 " 'materializedViews'. ")
            object_name = request.get("additionalFiltering", {}).get("objectName", None)
            if not chosen_objects_type_list and object_name:
                raise BadRequest("Can not extract object on name while not sending objectType")
            response = self.connect_to_jdbc(attributes=request.get("attributes"),
                                            user_id=self.user_isid,
                                            table_details=get_table_details,
                                            chosen_objects_type_list=chosen_objects_type_list,
                                            object_name=object_name)
            return response
        # as we can get both veeva_document and veeva_table as component_type_name
        if component_type_name.startswith("veeva"):
            document = not component_type_name == 'veeva_table'
            response = self.connect_to_veeva(attributes=request,
                                             table_details=get_table_details,
                                             document=document)
            return response
        raise BadRequest(f"Component type with name {component_type_name} is not supported")

    def connect_to_jdbc(self, attributes: list, user_id: str, table_details: bool,
                        chosen_objects_type_list: list = None, object_name: str = None):
        """
        Obtain connector object
        :param attributes:
        :param user_id:
        :param table_details:
        :param chosen_objects_type_list: list of objects which should be obtained from the DB, if None, get all
        :param object_name: name of object which information we wish to obtain
        :return: dictionary of items: list response
        """
        self.logger.info(f"User {user_id} is going to create connection to jdbc from request.")
        # try except block to catch database error, which is triggered if the connection is not made
        try:
            # we try to obtain inspector, if it fails, it should produce DatabaseError
            _, inspector = self._create_jdbc_connection(attributes, user_id=self.user_isid)
            list_of_objects_info = self.extract_object_details(inspector, table_details, chosen_objects_type_list,
                                                               object_name)
            return {"items": list_of_objects_info}
        except DatabaseError as exc:
            raise FailedConnectionError("Connection error during testing JDBC connection") from exc

    def create_s3_resource(self, attributes: list):
        """
        create s3 resource, if error occurs, we return False, as validation method returns needs this, to return
        invalid response and method for obtaining objects raises error, if this creation fails
        :param attributes:
        :return: s3 resource:
        """
        connect_info = self._parse_request_attributes(['s3_assume_role', "awsAssumedRole"],
                                                      attributes)
        region_name = self.project_settings_management.get_aws_region()
        try:
            if connect_info.get("s3_assume_role"):
                aws_access_key, aws_secret_key, aws_session_token = \
                    self.project_settings_management.assume_role_credentials(connect_info["s3_assume_role"],
                                                                             self.project_id + '_' +
                                                                             connect_info["awsAssumedRole"].split("/")[
                                                                                 1])
            else:
                aws_access_key, aws_secret_key, aws_session_token = \
                    self.project_settings_management.get_project_aws_account_access_info()

            s3_resource = boto3.Session(aws_access_key_id=aws_access_key,
                                        aws_secret_access_key=aws_secret_key,
                                        aws_session_token=aws_session_token,
                                        region_name=region_name).resource('s3')

            return s3_resource
        except ClientError:
            self.logger.exception("Connection error during testing S3 connection")
            # if any issue then return False, methods have separate handling for this response
            return False

    def _create_jdbc_connection(self, attributes: list, user_id: str):
        """
        Create/Connect to JDBC connection

        :param attributes:
        :param user_id:

        :return connection_jdbc, inspector
        """
        connect_info = self._parse_request_attributes(
            ['jdbc_user', 'jdbc_password', 'jdbc_url'], attributes)
        self.logger.info(f"User {user_id} is going to connect to jdbc.")
        jdbc_url = connect_info.get("jdbc_url")
        # if user sends in jdbc:oracle:thin or jdbc:postgresql in both cases, the connection type
        # is second string of the split string by ":"
        connection_type = jdbc_url.split(":")[1] if len(jdbc_url.split(":")) > 1 else "unsupported"
        if connection_type == "oracle":
            jdbc_url = jdbc_url.removeprefix("jdbc:oracle:thin:@")
            lib_dir = os.environ.get('LD_LIBRARY_PATH')
            init_oracle_client(lib_dir=lib_dir)
        elif connection_type == "postgresql":
            jdbc_url = jdbc_url.removeprefix("jdbc:postgresql://")
        elif connection_type == "redshift":
            jdbc_url = jdbc_url.removeprefix("jdbc:redshift://")
            connection_type = "redshift"
        else:
            raise BadRequest(f"Unsupported connection type: {connection_type}, please revalidate the connection url,"
                             " and recheck the format")
        # jdbc url should have lost its prefix, if it still there, we have mistake in prefix
        if jdbc_url == connect_info.get("jdbc_url"):
            raise BadRequest(f"Unsupported connection type: {connection_type}, please revalidate the connection url,"
                             " and recheck the format")
        split_url = jdbc_url.split(":")
        if len(split_url) > 2:
            # if its dbx url for databricks, then it is possible to pass the format as url:port:db
            # for the connection so just for now, we reparse it to use the / instead of the :
            # this is used only here for validation and obtaining tables, it has no effect on pipeline itself
            jdbc_url = split_url[0] + ":" + split_url[1] + "/" + split_url[2]
        connection_jdbc = create_engine(f"{connection_type}://"
                                        f"{connect_info.get('jdbc_user')}:{connect_info.get('jdbc_password')}@"
                                        f"{jdbc_url}")
        self.logger.info(f"Created connection is: {connection_jdbc}")
        inspector = inspect(connection_jdbc)
        return connection_jdbc, inspector

    # pylint: disable=too-many-locals
    def extract_object_details(self, inspector: inspect, table_details: bool, objects_to_extract: list = None,
                               target_object_name: str = None):
        """
        creates jdbc connection via sql alchemy and returns inspector
        :param inspector: sql_alchemy inspector object
        :param table_details:
        :param objects_to_extract: if given - string of option which objects from db we want to obtain
        :param target_object_name: object name of target object to be obtained
        :return: list containing dictionaries of table names and column info based on table_details flag
        """
        self.logger.info(f"Creating list of table information based on flag {table_details}")
        # if we do not have information which objects we want to obtain, we obtain all of them
        names_of_objects = []
        type_of_extracted_objects = []
        mapping_of_names = {"tables": "table", "views": "view", "materializedViews": "materializedView"}
        # Redshift get columns is not supported as of now
        if target_object_name and table_details:
            if inspector.bind.name == "redshift":
                raise BadRequest("Redshift does not support obtaining of column information")
            columns_info = self.get_columns_from_object(inspector, target_object_name)
            # objectType we collect as first entry, which is there
            return [{
                "objectName": target_object_name,
                "objectType": mapping_of_names.get(objects_to_extract[0]),
                "columns": columns_info
            }]
        # if we want only to collect general table information
        if not target_object_name:
            if not objects_to_extract:
                objects_to_extract = ["tables", "views", "materializedViews"]
            if "tables" in objects_to_extract:
                tables = inspector.get_table_names()
                names_of_objects.extend(tables)
                type_of_extracted_objects.extend(["table"] * len(tables))
            if "views" in objects_to_extract:
                views = inspector.get_view_names()
                names_of_objects.extend(views)
                type_of_extracted_objects.extend(["view"] * len(views))
            # redshift does not support the materialized views
            if "materializedViews" in objects_to_extract and inspector.bind.name != "redshift":
                materialized_views = inspector.get_materialized_view_names()
                names_of_objects.extend(materialized_views)
                type_of_extracted_objects.extend(["materializedView"] * len(materialized_views))
        out_list = []
        for type_of_extracted_object, name in zip(type_of_extracted_objects, names_of_objects):
            out_list.append({"objectName": name,
                             "objectType": type_of_extracted_object})
        return out_list

    @staticmethod
    def get_columns_from_object(inspector: inspect, name_of_object: str):
        """
        method which is called in multiple threads via executor.map
        :param inspector: sql_alchemy inspector object
        :param name_of_object:
        :return:
        """
        list_columns = []
        for column in inspector.get_columns(name_of_object):
            list_columns.append({
                "columnName": column.get('name'),
                "columnType": str(column.get('type'))
            })
        return list_columns

    # pylint: disable=too-many-locals
    def validate_connections(self, component_category: str, component_type_name: str,
                             request: dict):
        """
        Validate connection based on input connector information
        :param component_category:
        :param component_type_name:
        :param request:
        :return: list of
        """
        self.logger.info(f"Going to validate connection information for component category {component_category}"
                         f" and type {component_type_name}.")

        if component_type_name == "s3":
            return self._validate_s3_connection(request)
        # As of now only possible jdbc connection is oracle
        if component_type_name == 'jdbc':
            return self._validate_jdbc_connection(request)
        if component_type_name == 'sftp':
            return self._validate_sftp_connection(request)
        if component_type_name in ('veeva_table', 'veeva_document'):
            return self._validate_veeva_connection(request)
        raise BadRequest(f"Request is invalid. Component type {component_type_name} is not valid"
                         f" connector option for validation.")

    def _parse_request_attributes(self, attribute_names: [str], attributes) -> dict:
        """
        Loop all attributes and get values of attributes with names which are passed within attribute_names list

        :param attribute_names: list of attribute names
        :param attributes: attributes

        :return: dict of pair attribute : attribute value
        """
        if not attributes:
            return {}
        attr_values = {attribute_name: '' for attribute_name in attribute_names}
        for key in attr_values:
            for attribute in attributes:
                obj_type = attribute.get("type").get("objectType")
                if obj_type == "object":
                    attr_name = attribute.get('attributeName')
                    key_hierarchy = key.split("/")
                    if len(key_hierarchy) > 1 and key_hierarchy[0] == attr_name:
                        key_hierarchy.pop(0)
                        # loop inside with other inner attribute
                        result = self._parse_request_attributes(["/".join(key_hierarchy)],
                                                                attribute.get("type").get("attributes", []))
                        # there will be only one value and only this value will be assign to result
                        attr_values[key] = list(result.values())[0]
                elif key == attribute.get('attributeName'):
                    if obj_type == "secret":
                        attr_values[key] = self.get_secret_value(attribute.get('value').get("secretName"),
                                                                 attribute.get('value').get("secretKey"))
                    else:
                        attr_values[key] = attribute.get('value')
                    # the break here is needed, since there may be some extending files at end, which would break
                    # the code + optimisation bonus as we won't go through the whole for cycle, if key was found
                    break
        return attr_values

    def _validate_s3_connection(self, request):
        """
        Validate S3 connection
        Now check exactly objects folder of s3 given by bucket and prefix combination - if given
        :param request: request parameters
        :return: true/false flag if connection is valid or not
        """
        self.logger.info(f"User {self.user_isid} started _validate_s3_connection method with request: {request}")
        s3_resource = self.create_s3_resource(request["attributes"])
        if s3_resource:
            connect_info = self._parse_request_attributes(['source_s3_bucket'], request.get("attributes"))
            s3_bucket = connect_info.get("source_s3_bucket")
            try:
                objects_in_s3 = s3_resource.meta.client.list_objects_v2(Bucket=s3_bucket, Delimiter='/', Prefix="")
                # following condition checks, if there are any objects in the bucket
                if objects_in_s3:
                    return True
            except ClientError:
                self.logger.info(f"Connection to bucket {s3_bucket} is not valid")
        self.logger.info("Connection in not valid")
        return False

    def _validate_sftp_connection(self, request):
        """
        Validate SFTP connection

        :param request: request parameters
        :return: true/false flag if connection is valid or not
        """
        connect_info = self._parse_request_attributes(
            ['sftp_host', 'sftp_port', 'sftp_user', 'sftp_password', 'key/key_content'], request["attributes"])
        try:
            # using cnopts.hostkeys = None should not be used generally,
            # since it can be attacked via men in the middle, however we are taking the key from SM
            cnopts = pysftp.CnOpts()
            cnopts.hostkeys = None

            connections_parameters = {
                "host": connect_info.get("sftp_host"),
                "port": int(connect_info.get("sftp_port")),
                "username": connect_info.get("sftp_user"),
                "cnopts": cnopts,
            }
            if connect_info.get('key/key_content'):
                private_key_file = StringIO(connect_info.get('key/key_content'))
                private_key = paramiko.RSAKey(file_obj=private_key_file)
                connections_parameters["private_key"] = private_key
            if connect_info.get('sftp_password'):
                connections_parameters["password"] = connect_info.get('sftp_password')

            connection_sftp = pysftp.Connection(**connections_parameters)
            connection_sftp.close()
            return True
        except SSHException:
            self.logger.exception("Connection error during testing SFTP connection")
            # if any issue then return False
            return False

    def _validate_jdbc_connection(self, request):
        """
        Validate JDBC connection

        :param request: request parameters
        :return: true/false flag if connection is valid or not
        """
        try:
            _, inspector = self._create_jdbc_connection(request["attributes"], user_id=self.user_isid)
            if inspector.get_table_names():
                return True
        except DatabaseError:
            self.logger.exception("Connection error during testing JDBC connection")
            return False

    def get_secret_value(self, secret_name, secret_key):
        """
        Gets the secret for connection details.

        :param secret_name:
        :param secret_key:

        :return: secret value
        """
        if secret_name is None or secret_key is None:
            return None
        self.logger.info(f"Going to get secret value for secret with name {secret_name} and key {secret_key}.")
        secret_entity = self.secret_management.get_secret(
            secret_name=secret_name,
            get_values=True,
            raise_no_data_error=True,
            check_permission=False
        )
        if secret_key not in secret_entity.items:
            raise Exception(f"The secret  {secret_name} does not contain key {secret_key}")
        return secret_entity.items.get(secret_key)

    def _validate_veeva_connection(self, request):
        """
        Validate veeva connection, both veeva types are validated the same

        :param request: request parameters
        :return: true/false flag if connection is valid or not
        """
        self.logger.info(f"User {self.user_isid} wants to validate veeva_connection")
        response = self._create_veeva_connection(request, get_info=False)
        if response.json().get('responseStatus') == 'SUCCESS':
            self.logger.info('Connection result is SUCCESS')
            return True
        return False

    def connect_to_veeva(self, attributes, document: bool = False, table_details: bool = False):
        """
        This method is called if we are trying to get connector objects for veeva_table or
        veeva_document. As the API calls are almost same, it is possible to do it with only minor changes, which
        are passed via document boolean.

        :param attributes: request parameters
        :param table_details:
        :param document:
        :return: dictionary with "items": list of information about tables or documents
        """
        self.logger.info(f"User {self.user_isid} is trying to connect to veeva_table {not document} or "
                         f"veeva_document {document}, with table_details flag {table_details}")
        table_info = self._create_veeva_connection(attributes, True, document, table_details)
        return {"items": table_info}

    def _create_veeva_connection(self, request, get_info: bool = True, document: bool = False,
                                 table_details: bool = False):
        """
        This method is same for validation and getting connector objects, since we need to get
        first one post call, to obtain the sessionId for getting connector objects. This first one call is enough for
        validation. Getting connector objects is only if get_info is True (call from validation comes with
        get_info = False). As the veeva_document and veeva_table for obtaining connector objects
        have similar API approach, we can use them in similar manner.

        :param request: request body
        :param get_info:
        :param document:
        :param table_details:
        :return: true/false flag if connection is valid or not
        """
        self.logger.info(f"User {self.user_isid} is trying to connect to veeva_vault.")
        connection_attributes = next(
            (attribute for attribute in request['attributes'] if attribute['attributeName'] == 'connection'), None
        )
        if connection_attributes is None:
            raise BadRequest("The connection attributes could not be found.Please validate your request")
        connect_info = self._parse_request_attributes(
            ['username', 'password', 'vault_domain'], connection_attributes['type']['attributes'])
        username = connect_info.get('username')
        password = connect_info.get('password')
        vault_domain = connect_info.get('vault_domain')
        # extract api_version from attributes, if not given default it as v24.1
        api_version_attribute = next(
            (attribute for attribute in request['attributes'] if attribute['attributeName'] == 'api_version'), {}
        )
        api_version = api_version_attribute.get('value', 'v24.1')
        url_clean = f"https://{vault_domain}/api/{api_version}"
        # url with /auth is for validating of connection + we can obtain sessionId from it
        url_with_endpoint = url_clean + "/auth"
        try:
            response = requests.post(url_with_endpoint, headers={"Content-Type": "application/x-www-form-urlencoded"},
                                     data={"username": username, "password": password}, timeout=10)
        except NewConnectionError:
            self.logger.info('Connection error during testing veeva connection')
            return False
        # if we need to gather info from the table, the connection is done based on sessionId, which we need in first
        # place and then we can call the get calls
        if get_info:
            headers = {"Authorization": f"{response.json().get('sessionId')}"}
            objects_url = f"{url_clean}/metadata/objects/documents" if document else f"{url_clean}/metadata/vobjects"
            self.logger.info(
                f"User {self.user_isid} is trying to obtain connector objects from veeva vault with url {objects_url}.")
            # as the veeva vault was already validated, following get call should get though without error
            try:
                response = requests.get(objects_url, headers=headers, timeout=10)
            except NewConnectionError as exc:
                raise FailedConnectionError(f"Get call to veeva vault with url {objects_url} failed") from exc
            if response.json().get('responseStatus') == 'FAILURE':
                raise FailedConnectionError(f"Connection to veeva vault with url {objects_url} failed,"
                                            f" please revalidate the connection")
            table_info = []
            # as the objects are hidden under different keys for tables and documents in response, we need to specify it
            key_in_response = "types" if document else "objects"
            for vault_object in response.json().get(key_in_response):
                # if table_details are False, we need to limit the output - not yet sure on what, so we return only
                # urls and labels, for documents, these are only label + values variables in
                if not table_details and not document:
                    vault_object = {'url': vault_object.get('url'), 'label': vault_object.get('label')}
                # if we are extracting document, parse name into the output for better readability
                elif document:
                    vault_object.update({'name': vault_object.get('value', "").split('/')[-1]})
                table_info.append(vault_object)
            return table_info
        return response
