import ast
import inspect
import os
import shutil
import tempfile
import uuid
import importlib
import sys
from pathlib import Path
from typing import Optional
import re
import yaml
from github import Auth, Github

from common.helpers.exception import NotFoundError
from middleware.common.configuration.model_converter.configuration_to_model_converter import ConfigurationConverter
from middleware.common.entity_management.definitions_metadata_management import DefinitionsMetadataManagement
from middleware.common.entity_management.entities.entity_airflow_options import EntityAirflowOptions
from middleware.common.entity_management.entities.entity_object_run import EntityObjectRun
from middleware.common.entity_management.entities.entity_object_task_of_run import EntityObjectTaskOfRun
from middleware.common.entity_management.entities.entity_pipeline_steps import EntityPipelineSteps
from middleware.common.entity_management.entities.entity_project_account_settings import EntityProjectAccountSettings
from middleware.common.entity_management.entities.entity_subject import EntitySubject
from middleware.common.entity_management.platform_resources.resource_generator import ResourceGenerator
from middleware.common.helpers.airflow_eks_utils import AirflowEKSUtils
from middleware.common.helpers.datetime_formater import from_str_to_datetime
from middleware.common.metadatabase.model.types.component_type_categories_enum import ComponentTypeCategoriesEnum
from middleware.common.metadatabase.model.types.subjects_types_enum import SubjectTypesEnum
from middleware.common.entity_management.secrets_management import SecretsManagement
from middleware.common.metadatabase.model.types.project_account_types_enum import ProjectAccountTypesEnum
from middleware.common.entity_management.project_settings_management import ProjectSettingsManagement
from middleware.common.api_clients.airflow.airflow_api_client import AirflowApiClient
from middleware.common.entity_management.entity_management import EntityManagement


class ObjectsManagement(EntityManagement):
    """
    Main Objects management class
    """

    # pylint: disable=too-many-arguments
    # pylint: disable=too-many-instance-attributes
    # pylint: disable=duplicate-code
    # pylint: disable=too-many-public-methods
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._auth_validator = None
        self._secret_management = None
        self._project_settings_management = None
        self._resource_generator = None
        self._airflow_account_settings = None
        self._aws_account_settings = None
        self._databricks_account_settings = None
        self._model_converter = None
        self._configuration_converter = None
        self._airflow_api_client_map = {}
        self._definition_metadata_management = None
        project = EntitySubject.filter_subjects_by_type(SubjectTypesEnum.project, self.selected_subjects, uselist=False)
        self.project_id = project.subject_id if project is not None else None
        group = EntitySubject.filter_subjects_by_type(SubjectTypesEnum.group, self.selected_subjects, uselist=False)
        self.group_id = group.subject_id if group is not None else None
        self.selected_subject_ids = [subject.subject_id for subject in self.selected_subjects]
        self._aws_region = None

    @property
    def aws_region(self) -> str:
        """
        aws_region property which is passed in model convertor and resource generator in pipelines and pipelines
        templates
        """
        if self._aws_region is None:
            self._aws_region = self.project_settings_management.get_aws_region()
        return self._aws_region

    @property
    def configuration_converter(self) -> ConfigurationConverter:
        """
         model converter property
        """
        if not self._configuration_converter:
            self._configuration_converter = ConfigurationConverter(self.logger, self.secret_management,
                                                                   self.definition_metadata_management,
                                                                   self.user_isid, self.project_id)
        return self._configuration_converter

    @property
    def definition_metadata_management(self) -> DefinitionsMetadataManagement:
        """
        definition metadata management property
        """
        if self._definition_metadata_management is None:
            self._definition_metadata_management = DefinitionsMetadataManagement(
                logger=self.logger, metadatabase_connection=self.metadatabase_connection,
                lambda_secrets_manager=self.lambda_secrets_manager, user_isid=self.user_isid,
                selected_subjects=self.selected_subjects)
        return self._definition_metadata_management

    @property
    def airflow_account_settings(self) -> EntityProjectAccountSettings:
        """
        get airflow account settings
        """
        if not self._airflow_account_settings:
            self._airflow_account_settings = self.project_settings_management.get_project_account_settings(
                account_type=ProjectAccountTypesEnum.airflow,
                check_permission=False,
                raise_not_found_error=True
            )
        return self._airflow_account_settings

    @property
    def aws_account_settings(self) -> EntityProjectAccountSettings:
        """
        get aws account settings
        """
        if not self._aws_account_settings:
            self._aws_account_settings = self.project_settings_management.get_project_account_settings(
                account_type=ProjectAccountTypesEnum.aws,
                check_permission=False,
                raise_not_found_error=True
            )
        return self._aws_account_settings

    @property
    def databricks_account_settings(self) -> EntityProjectAccountSettings:
        """
        get databricks account settings
        """
        if not self._databricks_account_settings:
            self._databricks_account_settings = self.project_settings_management.get_project_account_settings(
                account_type=ProjectAccountTypesEnum.databricks,
                check_permission=False,
                raise_not_found_error=True
            )
        return self._databricks_account_settings

    @property
    def project_settings_management(self) -> ProjectSettingsManagement:
        """
        project settings management property
        """
        if self._project_settings_management is None:
            self._project_settings_management = ProjectSettingsManagement(
                logger=self.logger,
                metadatabase_connection=self.metadatabase_connection,
                lambda_secrets_manager=self.lambda_secrets_manager,
                user_isid=self.user_isid,
                selected_subjects=self.selected_subjects
            )
        return self._project_settings_management

    @property
    def secret_management(self) -> SecretsManagement:
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

    def get_and_resolve_airflow_api_client(self, project_id) -> AirflowApiClient:
        """
        get and resolve airflow api client
        @param project_id: project id for which we want to obtain airflow api client
        @return: airflow api client
        @rtype: AirflowApiClient
        """
        if project_id is None:
            project_id = self.project_id
        api_client = self._airflow_api_client_map.get(project_id)
        if not api_client:
            if project_id != self.project_id:
                api_client = self.project_settings_management. \
                    get_shared_project_specific_airflow_api_client(project_id=project_id)
            else:
                api_client = AirflowApiClient(
                    self.airflow_account_settings.account_details, self.logger, self.secret_management)
            self._airflow_api_client_map[project_id] = api_client
        return api_client

    def get_objects_runs(self, dag_id: str, max_result: int, project_id: str = None) -> [EntityObjectRun]:
        """
        Get runs of objects. The method hit airflow api to get all dag runs

        @param dag_id: input dag id to inspect
        @param max_result: max results of items in response
        @param project_id: str - project_id of the project owner of the object
        @return: list of EntityObjectRun
        """
        self.logger.info(
            f"Calling get_objects_runs with parameters dag_id={dag_id}, max_result={max_result}")
        if not dag_id:
            self.logger.warning("Dag is is empty. Not able to retrieve objects runs")
            return []
        # if project_id was passed, the project owner is different from current owner
        # we need to obtain project_specific_airflow_api_client
        object_runs = self.get_and_resolve_airflow_api_client(project_id=project_id). \
            get_dag_runs(dag_id, limit=max_result, order_by="-execution_date")
        result_object_runs = []
        for run in object_runs.dag_runs:
            # In case when you have the call the api and there any active runs
            # then end date will be None which will raise errors.so checking  none condition for only end date
            # to avoid failure of code
            result_object_runs.append(
                EntityObjectRun(run_id=run['dag_run_id'],
                                start_date=from_str_to_datetime(run['start_date'], date_format=None),
                                end_date=from_str_to_datetime(run['end_date'], date_format=None),
                                logical_date=from_str_to_datetime(run['logical_date'], date_format=None),
                                state=run['state'],
                                run_type=run['run_type']))

        return result_object_runs

    def get_tasks_of_object_runs_from_api(self, dag_id: str, dag_run_id: str,
                                          project_id: str = None) -> [EntityObjectRun]:
        """
        Get tasks of runs of objects. This is equivalent to task instances in airflow

        @param dag_id: input dag id to inspect
        @param dag_run_id: run id of dag
        @param project_id: str - project_id of the project owner of the object
        @return: list of EntityObjectRun
        """
        self.logger.info(
            f"Calling get_tasks_of_object_runs with parameters dag_id={dag_id}, dag_run_id={dag_run_id}")
        if not dag_id:
            self.logger.warning("Dag is is empty. Not able to retrieve tasks of runs of objects")
            return []
        task_instances = self.get_and_resolve_airflow_api_client(project_id=project_id) \
            .get_task_instances(dag_id, dag_run_id=dag_run_id)
        result_task_instances = []
        for task_instance in task_instances.task_instances:
            result_task_instances.append(
                EntityObjectTaskOfRun(
                    task_id=task_instance['task_id'],
                    start_date=from_str_to_datetime(task_instance['start_date'], date_format='%Y-%m-%dT%H:%M:%S.%f%z'),
                    duration=task_instance['duration'], state=task_instance['state'],
                    try_number=1 if task_instance['try_number'] == 0 and task_instance['state']
                                    in ("success", "failed", "deferred") else task_instance['try_number'])
            )

        return result_task_instances

    def get_logs_of_task_from_api(self, dag_id: str, dag_run_id: str, task_id: str, try_number: int = 1,
                                  project_id: str = None) -> Optional[str]:
        """
        Get logs of task instance directly from airflow

        @param dag_id: input dag id to inspect
        @param dag_run_id: run id of dag
        @param task_id: id of task/task instance
        @param try_number: try number of task instance run
        @param project_id: str - project_id of the project owner of the object
        @return: log in str format
        """
        if not dag_id:
            self.logger.warning("Dag is is empty. Not able to retrieve task logs")
            return None
        # if project_id was passed, the project owner is different from current owner
        # we need to obtain project_specific_airflow_api_client
        self.logger.info(
            f"Calling get_logs_of_task with parameters dag_id={dag_id}, dag_run_id={dag_run_id}, "
            f"task_id={task_id}, try_number={try_number}")
        str_log: str = self.get_and_resolve_airflow_api_client(project_id=project_id). \
            get_task_instance_logs(dag_id=dag_id, dag_run_id=dag_run_id, task_id=task_id, try_number=try_number)
        return str_log

    def get_first_and_last_steps_connectors(self, steps: [EntityPipelineSteps] = None):
        """
        Fetch the first and last connector details in the given pipeline template flow.

        :param steps

        returns first_input_connector and last_output_connector
        """

        self.logger.info("Going to resolve first and last connector")
        first_input_connector = None
        last_output_connector = None
        if not steps:
            return first_input_connector, last_output_connector
        # first order steps
        child_to_parent_hierarchy = dict()
        last_child_name = "__LAST_STEP__"
        for step in steps:
            child_name = step.child_component_name
            if not child_name:
                child_name = last_child_name
            child_to_parent_hierarchy[child_name] = step

        # loop from last to first and add to o
        while child_to_parent_hierarchy:
            if last_child_name not in child_to_parent_hierarchy:
                # in case, that hierarchy is not complete then return none values
                return None, None
            step = child_to_parent_hierarchy.pop(last_child_name)
            last_child_name = step.component_name
            # loop from behind so the first output connector in loop is last connector in result
            if not last_output_connector and \
                    step.definition.get('componentCategory') == ComponentTypeCategoriesEnum.output_connector.value:
                last_output_connector = step.definition.get('componentType')
            # loop from behind then the last input connector in loop is the first input connector in result
            if step.definition.get('componentCategory') == ComponentTypeCategoriesEnum.input_connector.value:
                first_input_connector = step.definition.get('componentType')

        return first_input_connector, last_output_connector

    @property
    def resource_generator(self):
        """
        Pipeline template metadata provider
        """
        if self._resource_generator is None:
            self._project_settings_management = ResourceGenerator(
                logger=self.logger,
                aws_region=self.aws_region,
                secret_management=self.secret_management,
                airflow_instance_settings=self.airflow_account_settings.account_details,
                aws_access_key=self.aws_access_key, aws_secret_key=self.aws_secret_key,
                aws_session_token=self.aws_session_token)
        return self._project_settings_management

    def delete_object_from_airflow(self, dag_id):
        """
        Delete object (pipeline/workflow) from airflow

        @param dag_id: ID of dag
        """
        self.logger.info(f"Going to delete airflow dag with name  {dag_id}")
        # first delete the dag from EKS repo:
        tmp_folder = "/tmp"
        tmp_folder_prefix = uuid.uuid4().hex
        # make an airflow call to get dag details specially to retrieve file loc details
        # for example this is how fileloc from airflow looks like -
        # /usr/local/airflow/mnt/arfrepo/dags/S3_TO_S3_KP4_dev_dag_out_dir/dag.py , we are picking
        # dag folder name by spilting the fileloc on basis of "/" delimiter.
        # first check if the dag is present or not in airflow , if it doesn't exist
        # instead of skipping the dag clean up from EKS and clean pipeline only from DB will
        # result in  partial cleanup hence it is good idea to raise we are raising error .
        try:
            dag_name = self.get_and_resolve_airflow_api_client(
                project_id=self.project_id).get_dag(dag_id).fileloc.split("/")[-2]
        except NotFoundError as exc:
            # if the DAG was deleted or can not be found just log the error and proceed with deleteion
            self.logger.info(f"Airflow DAG {dag_id} does not exist. The deletion of DAG from EKS repo cannot be done"
                             f" deletion of pipeline will proceed. Not found error log: {exc}")
        airflow_settings = self.airflow_account_settings.to_json_dict()
        with tempfile.TemporaryDirectory(prefix=tmp_folder_prefix, dir=tmp_folder) as tmpdir:
            AirflowEKSUtils(airflow_instance_settings=airflow_settings,
                            secret_management=self.secret_management,
                            logger=self.logger, workspace=tmpdir). \
                delete_dag_from_eks_repo(dag_name)
        # call Airflow API to delete DAG, in case if the call is not successful then API would return 500 error.
        try:
            self.get_and_resolve_airflow_api_client(project_id=self.project_id).delete_dag(dag_id=dag_id)
        except NotFoundError:
            self.logger.info(f"Airflow DAG {dag_id} does not exists. The deletion of DAG will be skipped")

    def create_yaml_configuration_file(self, dataset_name: str, tmpdir: str, yaml_configuration: dict):
        """
        Create yaml configuration file for

        @param dataset_name:
        @param tmpdir:
        @param yaml_configuration:
        """
        self.logger.info(f"Create yaml configuration file for dataset {dataset_name}")
        conf_path = f'{tmpdir}{os.path.sep}{dataset_name}{os.path.sep}conf'
        Path(conf_path).mkdir(parents=True, exist_ok=True)
        os.chdir(f'{tmpdir}{os.path.sep}{dataset_name}{os.path.sep}conf')
        with open(f"{conf_path}{os.path.sep}dataset_definition.yaml", 'w', encoding='utf-8') as dataset_file:
            if "dataset_name" not in yaml_configuration:
                dataset_file.write(f"dataset_name: {dataset_name}\n")
            dataset_file.write(yaml.dump(yaml_configuration))

    def run_resource_generator(self, **args) -> None:
        """
        Run resource generator

        @param args: dict of the following args
        - tmpdir
        - dataset_name
        - source_code_folder
        - object_version
        - framework_version
        - environment

        @return: None
        """
        self.logger.info("Run resource generator,...")
        tmpdir = args["tmpdir"]
        dataset_name = args["dataset_name"]
        source_code_folder = args["source_code_folder"]
        object_version = args["object_version"]
        framework_version = args["framework_version"]
        environment = args["environment"]

        shutil.copytree(f'{source_code_folder}{os.path.sep}framework_jobs',
                        f'{tmpdir}{os.path.sep}framework_jobs')
        # copy requirements files to the lambda workspace
        shutil.copytree(f'{source_code_folder}{os.path.sep}deploy{os.path.sep}packaging',
                        f'{tmpdir}{os.path.sep}deploy{os.path.sep}packaging')
        self.resource_generator.run_platform_generator(
            dataset_name=dataset_name,
            pipeline_version=object_version,
            framework_version=framework_version,
            source_dir=tmpdir,
            optional_fields={"env": environment}
        )

    @staticmethod
    def import_path(path):
        """
        Method for loading .py file from local workspace and import it as a module

        @param path:
        """
        module_name = os.path.basename(path).replace('-', '_')
        spec = importlib.util.spec_from_loader(
            module_name,
            importlib.machinery.SourceFileLoader(module_name, path)
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        sys.modules[module_name] = module
        return module

    def process_orchestration(self, **args) -> (str, str):
        """
        Process orchestration

        @param args: dict of the following args
        - tmpdir
        - dataset_name
        - object_version
        - environment

        @return: (airflow link, dag name)
        """
        tmpdir = args["tmpdir"]
        dataset_name = args["dataset_name"]
        framework_version = args["framework_version"]
        environment = args["environment"]
        airflow_info = self.airflow_account_settings.account_details['apiAccess']
        pipeline_definitions = self.resource_generator.create_and_deploy_airflow_dag(
            dataset_name, framework_version, tmpdir, airflow_info,
            {"env": environment, "project_name": self.project_id})
        os.chdir(f'{tmpdir}{os.path.sep}{dataset_name}{os.path.sep}conf')
        if not pipeline_definitions:
            # find definition path in dir if it is not defined from generator, based on dataset name
            pipeline_definitions_py_file = [str(path) for path in
                                            Path(tmpdir).rglob(f'configuration_provider_{dataset_name}*')][0]
            self.logger.info(f"Collected path of file is {pipeline_definitions_py_file}")
            pipeline_definitions = [self.import_path(pipeline_definitions_py_file).INPUT]
        # update the created status in db to true on successful creation of pipeline
        airflow_host = self.airflow_account_settings.account_details['apiAccess']['airflowHost']
        if not airflow_host.startswith("http"):
            airflow_host = f"https://{airflow_host}"
        airflow_link = f"{airflow_host}/dags/{pipeline_definitions[0]['dag_name']}/grid"
        # remove airflow variable which driven scheduler
        self.get_and_resolve_airflow_api_client(
            project_id=self.project_id).remove_variable(f"{pipeline_definitions[0]['dag_name']}.schedule")
        self.logger.info(f"Output airflow link {airflow_link} and dag name {pipeline_definitions[0]['dag_name']}")
        return airflow_link, pipeline_definitions[0]['dag_name']

    def _get_object_airflow_details(self, dag_id, project_id: str = None) -> (str, str, str, str):
        """
        Enrich entity pipeline with details from airflow.

        @param dag_id: dag id
        @param project_id: str project_id of project owner of object
        """
        dag_details = None
        next_dagrun = None
        start_date = None
        last_runtime = None
        # if following api calls fails and status was not set yet, current status of None would be returned and
        # as such, we need to preset the status, which if not correctly replaced will be returned
        status = "airflowError"
        # if project_id was passed, the project owner is different from current owner
        # we need to obtain project_specific_airflow_api_client
        airflow_api_client = self.get_and_resolve_airflow_api_client(project_id=project_id)
        try:
            try:
                dag_details = airflow_api_client.get_dag(dag_id)
            except NotFoundError:
                self.logger.info(f"Airflow does not yet have information about dag with id {dag_id}")
                status = "dagNotAvailable"
            if dag_details:
                next_dagrun = from_str_to_datetime(dag_details.next_dagrun, date_format=None)
                # as we need to get the status from all runs if any of them is running, we need to obtain run history
                dag_run_details_running = airflow_api_client.get_dag_runs(dag_id, order_by="-execution_date",
                                                                          get_running=True)
                # if there are any running, set status as running
                if dag_run_details_running and dag_run_details_running.dag_runs:
                    status = "running"
                dag_run_details_last = airflow_api_client.get_dag_runs(dag_id, limit=1, order_by="-execution_date",
                                                                       get_running=False)
                if dag_run_details_last and dag_run_details_last.dag_runs:
                    # if status is not running, there are no running, obtain status based on the outcome of the last run
                    if status != "running":
                        status = dag_run_details_last.dag_runs[0].get('state', 'none')
                    # set information of last run
                    start_date = dag_run_details_last.dag_runs[0].get('start_date')
                    start_date = from_str_to_datetime(start_date, date_format=None)
                    end_date = dag_run_details_last.dag_runs[0].get('end_date')
                    end_date = from_str_to_datetime(end_date, date_format=None)
                    last_runtime = str(end_date - start_date) if end_date is not None and start_date is not None \
                        else None
                else:
                    self.logger.warning(f"The dag id {dag_id} does not have active dag runs in Airflow")
                    status = "noRuns"
        # pylint: disable=broad-except
        except Exception as exc:
            # catch all error. Do not prevent to retrieve pipeline data because of some unavailability of airflow API
            # or because of some settings in project, raising of the error would not set the airflow status to error
            self.logger.exception(f"There is unexpected error during loading data from Airflow, error log: {exc}")
        return next_dagrun, start_date, last_runtime, status

    def calculate_available_tags_limit(self):
        """
        Calculate the remaining available tags count based on the total allowed, default project settings
        tags, and pipeline tags.

        @return: The number of available tag slots.
        """
        # default pipeline tags (pipeline_version, framework_version)
        model_convertor_default_tags_count = 2

        # hard coding it to 10 as it is the maximum limit from aws glue side.
        glue_total_tags_allowed = 10

        # now calculate the remaining tags count that is user is allowed to input from UI.
        glue_max_tags_count = glue_total_tags_allowed - model_convertor_default_tags_count

        # hard coding it to 10 as it is the maximum limit from databricks side.
        dbx_total_tags_allowed = 25

        # get the default tags count that are defined under project settings.
        project_dbx_settings = self.project_settings_management.get_project_account_settings(
            ProjectAccountTypesEnum.databricks)

        # Now calculate the default tags count
        default_project_settings_tags_count = len(
            project_dbx_settings.account_details.get('tags', []))

        # now calculate the remaining tags count that is user is allowed to input from UI.
        dbx_max_tags_count = dbx_total_tags_allowed - (default_project_settings_tags_count +
                                                       model_convertor_default_tags_count)

        return glue_max_tags_count, dbx_max_tags_count

    # pylint: disable=too-many-locals
    def update_key_in_configuration_provider(self, object_name: str, key_to_rewrite: str, new_value):
        """
        Update key in configuration provider,
        @param object_name: object_name of the object whose property is to be updated, is same as dataset name
        @param key_to_rewrite: key to value
        @param new_value: new value to write under the key, can be of any type
        """
        airflow_settings = self.airflow_account_settings.to_json_dict()["eksBased"]
        token = self.secret_management.get_secret(
            airflow_settings["eksGitAccessToken"]["secretName"], get_values=True,
            check_permission=False).items.get(airflow_settings["eksGitAccessToken"]["secretKey"])
        # collect branch name from airflow settings
        branch_name = airflow_settings["branchName"]
        # collect dag folder from airflow settings
        branch_dag_folder = airflow_settings["branchDagFolder"]
        # drop the prefix, as we need to extract only the repo path
        repo_path = airflow_settings["repositoryUrl"].removeprefix("https://github.com/")
        # prepare the github client
        auth = Auth.Token(token)
        # need to use verify false else we run into SSL issues on the deployed lambda
        github_client = Github(auth=auth, verify=False)
        # obtain target repo
        target_repo = github_client.get_repo(repo_path)
        # file path in the repository path is dynamic with some static keys
        file_path = f"{branch_dag_folder}/{object_name}_{self.project_settings_management.get_project_environment()}" \
                    f"_dag_out_dir/configuration_provider_{object_name}.py"
        # read the configuration provider file
        configuration_provider_file = target_repo.get_contents(file_path, ref=branch_name)
        file_content = configuration_provider_file.decoded_content.decode('utf-8')

        configuration_provider_file_updated = self.regex_operations_on_stringed_input(
            stringed_input=file_content,
            key_to_change=key_to_rewrite,
            new_value=new_value)

        # update target file back in the repo
        target_repo.update_file(file_path, f"Update {key_to_rewrite} value for object name {object_name}",
                                configuration_provider_file_updated,
                                configuration_provider_file.sha, branch=branch_name)

    def regex_operations_on_stringed_input(self, stringed_input, key_to_change: str, new_value) -> str:
        """
        Regex operations on stringed file to update the key value pair in the file
        handles the SecretValue attributes, as the ast.literal_eval can not parse them
        @stringed_input: stringed content -
        @key_to_change: key to change in the stringed input
        @new_value: new value to write under the key
        @return: updated stringed file
        @rtype: str
        """
        self.logger.info("Starting method regex_operations_on_stringed_input")
        # regex the whole line starting with the INPUT
        pattern = r'^(INPUT\s*=\s*{.*?})$'
        input_match = re.search(pattern, stringed_input, flags=re.MULTILINE)
        input_line = input_match.group(1)
        input_dict_str = input_line.removeprefix("INPUT = ")
        # need to have ast literal eval, because json.loads does not support single quotes
        # replace all SecretValue instances with unique placeholders - as ast.literal eval can not parse
        # secret value values
        secret_value_pattern = re.compile(r'SecretValue\([^)]+\)')
        placeholders = []
        modified_str = input_dict_str
        # replace each instance of secret value with placeholder string
        for index, match in enumerate(secret_value_pattern.findall(input_dict_str)):
            placeholder = f"__SECRET_VALUE__{index}"
            placeholders.append((placeholder, match))
            modified_str = modified_str.replace(match, f"'{placeholder}'")

        # read the string as dictionary
        evaluated_dict = ast.literal_eval(modified_str)
        # rewrite property with new value
        evaluated_dict[key_to_change] = new_value

        # convert it back to the string representation - can not use json.dumps as is casts it with double quotes
        result_str = repr(evaluated_dict)

        # replace the placeholders back with SecretValue instances
        for placeholder, original in placeholders:
            result_str = result_str.replace(f"'{placeholder}'", original)

        # save it back to the string in the output file
        modified_input_line = 'INPUT = ' + result_str
        updated_stringed_input = re.sub(pattern, modified_input_line, stringed_input, flags=re.MULTILINE)
        self.logger.info("Finished method regex_operations_on_stringed_input")
        return updated_stringed_input

    def check_or_create_airflow_pool(self, airflow_advanced_settings: EntityAirflowOptions) -> None:
        """
        Check if airflow pool exists, if not, create it

        @param airflow_advanced_settings: object specific airflow settings
        @return: None
        """
        self.logger.info("Starting method get_or_create_airflow_pool")
        pool_name = airflow_advanced_settings.airflow_pool_name
        # if pool_name was not given, it is defaulted in the airflow and there is no need to obtain it or create it
        if pool_name:
            airflow_api_client = self.get_and_resolve_airflow_api_client(project_id=self.project_id)

            # try to obtain the pool, if it exists
            existing_pool = airflow_api_client.get_pool(pool_name=pool_name)
            if existing_pool:
                self.logger.info(f"Found existing poole with name {pool_name} and slots {existing_pool.slots}")
                return
            pool_slots = airflow_advanced_settings.airflow_pool_slots if airflow_advanced_settings.airflow_pool_slots \
                else 128

            # as the pool was not found, we need to create it with specified name and slots
            airflow_api_client.create_pool(pool_name=pool_name, pool_slots=pool_slots)
            self.logger.info(f"Created pool with name {pool_name} and slots {pool_slots}")

    @staticmethod
    def generate_dataset_pom_file(object_name: str, project_group_id: str):
        """
        generate pom file.

        @param object_name.
        @param project_group_id

        @return pom file
        """
        return inspect.cleandoc(f"""
        <project xmlns="http://maven.apache.org/POM/4.0.0" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
            xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 http://maven.apache.org/xsd/maven-4.0.0.xsd">
            <modelVersion>4.0.0</modelVersion>

            <parent>
                <!-- Replace your parent pom file-->
            </parent>

            <packaging>pom</packaging>
            <groupId>{project_group_id}</groupId>
            <artifactId>{object_name}</artifactId>
            <version>1.0.0-SNAPSHOT</version>
        </project>
        """)
