import os

from middleware.common.entity_management.secrets_management import SecretsManagement
from middleware.common.helpers.github_repo import GithubRepo


class DatasetRepoUtils(GithubRepo):
    """
     class sets up the util for exporting  dataset config to dataset repository
    """

    def __init__(self, github_settings, secret_management: SecretsManagement, workspace, logger, branch_name,
                 folder_to_store):
        """
        Initialize connection to airflow server or connection to project github datasets repository
        """

        super().__init__(logger, git_url=github_settings['url'], branch_name=branch_name)
        self.workspace = workspace
        self.repo_directory = f"{workspace}{os.path.sep}dataset-repository"
        self.secret_management = secret_management
        self._git_user_name = None
        self._git_user_pass = None
        self.github_settings = github_settings
        self.folder_to_store = folder_to_store
        self.init_repo(self.repo_directory)

    def get_repo_credentials(self):
        """
        property git repo credentials
        """
        if self._git_user_name is None:
            self._git_user_name = self.github_settings["username"]
            self._git_user_pass = self.secret_management.get_secret(
                self.github_settings["accessToken"]["secretName"], get_values=True,
                check_permission=False
            ).items.get(self.github_settings["accessToken"]["secretKey"])
        return self._git_user_name, self._git_user_pass

    def upload_dataset_file_to_repo(self, pipeline_name):
        """
        Upload the dataset to the project dataset repo.

        :param pipeline_name
        """

        dataset = f"{pipeline_name}"
        dst_folder = f'{self.repo_directory}{os.path.sep}{self.folder_to_store}' \
                     f'{os.path.sep}{dataset}'
        src_folder = f"{self.workspace}{os.path.sep}{dataset}"

        commit_message = f'NGA-0: Add new dataset {pipeline_name} into {self.branch_name} into' \
                         f' {dst_folder}'

        return self.copy_folder_to_repo(commit_message=commit_message,
                                        src_folder=src_folder, dst_folder=dst_folder)