import os
from middleware.common.entity_management.secrets_management import SecretsManagement
from middleware.common.helpers.github_repo import GithubRepo


class AirflowEKSUtils(GithubRepo):
    """
    class sets up the util for airflow DAG copy to server
    """

    def __init__(self, airflow_instance_settings, secret_management: SecretsManagement, logger, workspace):
        """
        Initialize connection to airflow server
        """
        super().__init__(logger, git_url=airflow_instance_settings["eksBased"]["repositoryUrl"],
                         branch_name=airflow_instance_settings["eksBased"]["branchName"])
        self.airflow_instance_eks_settings = airflow_instance_settings["eksBased"]
        self.workspace = workspace
        self.secret_management = secret_management
        self.repo_directory = f"{workspace}{os.path.sep}dag-repository"
        self._git_user_name = None
        self._git_user_pass = None
        self.init_repo(self.repo_directory)

    def get_repo_credentials(self):
        """
        Property eks_repo_credentials
        """
        if self._git_user_name is None:
            self._git_user_name = self.airflow_instance_eks_settings["eksGitUsername"]
            self._git_user_pass = self.secret_management.get_secret(
                self.airflow_instance_eks_settings["eksGitAccessToken"]["secretName"], get_values=True,
                check_permission=False
            ).items.get(self.airflow_instance_eks_settings["eksGitAccessToken"]["secretKey"])
        return self._git_user_name, self._git_user_pass

    def upload_to_eks_repo(self, pipeline_name, **optional_fields):
        """
        Upload the dag to eks repo. It means that dag_payload is copy to local repo, commit and push into remote repo
        """
        dag_payload = f"{pipeline_name}_{optional_fields.get('env', 'dev')}_dag_out_dir"
        dst_folder = f'{self.repo_directory}{os.path.sep}{self.airflow_instance_eks_settings["branchDagFolder"]}' \
                     f'{os.path.sep}{dag_payload}'

        src_folder = f"{self.workspace}{os.path.sep}{dag_payload}"

        commit_message = f'NGA-0: Add new DAG {pipeline_name} into ' \
                         f'{self.airflow_instance_eks_settings["branchName"]} into {dst_folder}'
        return self.copy_folder_to_repo(commit_message=commit_message,
                                        src_folder=src_folder, dst_folder=dst_folder)

    def delete_dag_from_eks_repo(self, dag_name):
        """
        Delete the DAG folder from the EKS repository.

        @param dag_name
        """
        dst_folder = f'{self.repo_directory}{os.path.sep}{self.airflow_instance_eks_settings["branchDagFolder"]}' \
                     f'{os.path.sep}{dag_name}'
        # Commit and push the deletion
        commit_message = f'NGA-0: Delete DAG {dag_name} from {self.airflow_instance_eks_settings["branchName"]}'
        return self.delete_folder_from_repo(commit_message=commit_message, folder_path=dst_folder)