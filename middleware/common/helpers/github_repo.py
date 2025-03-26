import os
import shutil
from abc import ABCMeta, abstractmethod

from git import Repo, GitCommandError


class GithubRepo(metaclass=ABCMeta):
    """
    Abstract class for interacting with GitHub repositories.
    """

    def __init__(self, logger, git_url, branch_name):
        self.logger = logger
        self.branch_name = branch_name
        self.git_url = git_url
        self.git_repo = None

    @abstractmethod
    def get_repo_credentials(self) -> (str, str):
        """
        Abstract method to get repository credentials.

        """

    def init_repo(self, repo_directory: str):
        """
        Creates or clones the repository to the specified directory.

        @param repo_directory: Local directory where the repository will be cloned.

        raises Exception: If there is an issue removing the existing directory or cloning the repository.
        """
        git_username, git_password = self.get_repo_credentials()
        if os.path.exists(repo_directory):
            self.logger.info(f"{repo_directory} exists. Removing before cloning.")
            shutil.rmtree(repo_directory)
        self.logger.info(f"Cloning repository {self.git_url}...")
        self.git_repo = Repo.clone_from(
            f'https://{git_username}:{git_password}@{self.git_url.replace("https://", "")}',
            repo_directory,
            branch=self.branch_name,
            depth=1
        )
        self._configure_repo_user(git_username)

    def _configure_repo_user(self, git_username: str):
        """
        Configures the Git user settings for the repository.

        @param git_username: GitHub username to configure.
        """
        self.git_repo.config_writer().set_value("user", "name", git_username).release()
        self.git_repo.config_writer().set_value("user", "email", f"{git_username}@example.com").release()

    def _remove_directory_if_exists(self, path: str, raise_exception: bool = False):
        """
        Removes the directory if it exists.

        @param path: Path to the directory.
        @param raise_exception: If True, raises an exception if the directory does not exist.
        @raises Exception: If raise_exception is True and the directory does not exist.
        """
        if os.path.exists(path):
            self.logger.info(f"{path} exists. Removing it.")
            shutil.rmtree(path)
        elif raise_exception:
            raise Exception(f"The specified directory {path} doesn't exist.")

    def _commit_and_push_changes(self, commit_message: str):
        """
        Commits and pushes changes to the remote repository.

        @param commit_message: Commit message describing the changes.

        raises GitCommandError: If there is an issue with Git commands or warns if
        no changes are detected
        """
        try:
            git_username, _ = self.get_repo_credentials()
            self.logger.info("Running Git add command")
            self.git_repo.git.add(all=True)
            self.logger.info("Committing changes to local repository")
            author_info = f'--author={git_username} <{git_username}@example.com>'
            self.git_repo.git.commit(author_info, '-m', commit_message)
            self.logger.info(f"Pushing changes to branch {self.branch_name}")
            self.git_repo.git.push('origin', self.branch_name)
        except GitCommandError as git_cmd_err:
            if 'nothing to commit, working tree clean' in str(git_cmd_err):
                self.logger.warning(str(git_cmd_err))
            else:
                raise

    def copy_folder_to_repo(self, commit_message: str, src_folder: str, dst_folder: str):
        """
        Copies a folder from the local system to the repository and commits the changes.

        @param commit_message: Commit message describing the changes.
        @param src_folder: Source folder path to copy from.
        @param dst_folder: Destination folder path in the repository.

        """
        self._remove_directory_if_exists(dst_folder, raise_exception=False)
        shutil.copytree(src_folder, dst_folder)
        self.logger.info(f"Copied {src_folder} to {dst_folder}")
        self._commit_and_push_changes(commit_message)

    def delete_folder_from_repo(self, folder_path: str, commit_message: str):
        """
        Deletes a folder from the repository and commits the change.

        @param folder_path: Path to the folder in the repository to be deleted.
        @param commit_message: Commit message describing the deletion.

        """
        self._remove_directory_if_exists(folder_path, raise_exception=True)
        self._commit_and_push_changes(commit_message)