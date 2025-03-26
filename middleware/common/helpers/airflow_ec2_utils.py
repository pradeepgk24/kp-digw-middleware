import os
import io
from stat import S_ISDIR
import paramiko

from middleware.common.entity_management.secrets_management import SecretsManagement


class AirflowEC2Utils:
    """
    class sets up the util for airflow DAG copy to server
    """

    def __init__(self, airflow_instance_settings, secret_management: SecretsManagement, logger,
                 region_name="us-east-1"):
        """
        Initialize connection to airflow server
        """
        self.airflow_instance_ec2_settings = airflow_instance_settings["ec2Based"]
        self.logger = logger
        self.region = region_name
        self.dag_folder = airflow_instance_settings["ec2Based"]["airflowDagFolder"]
        self._sftp_client = None
        self.secret_management = secret_management

    @property
    def sftp_client(self):
        """
        Property sftp_client
        """
        if self._sftp_client is None:
            secret_manager_ppk = self.airflow_instance_ec2_settings['sshCredentialsPrivateKey']['secretName']
            secret_manager_ppk_key = self.airflow_instance_ec2_settings['sshCredentialsPrivateKey']['secretKey']
            self.logger.info("Going to connect to Airflow SFTP with following parameters:\n"
                             f"airflowHost={self.airflow_instance_ec2_settings['airflowHost']}\n"
                             f"airflowPort={self.airflow_instance_ec2_settings['airflowPort']}\n"
                             f"sshCredentialsSM={secret_manager_ppk}\n"
                             f"")

            transport_session = paramiko.Transport(
                (
                    self.airflow_instance_ec2_settings["airflowHost"],
                    int(self.airflow_instance_ec2_settings["airflowPort"])
                )
            )
            # retrieve PPK from secret
            ppk_key = self.secret_management.get_secret(
                secret_manager_ppk, get_values=True, check_permission=False
            ).items[secret_manager_ppk_key]
            transport_session.connect(
                username=self.airflow_instance_ec2_settings["sshCredentialsUsername"],
                pkey=paramiko.RSAKey.from_private_key(io.StringIO(str(ppk_key)))
            )
            self._sftp_client = paramiko.SFTPClient.from_transport(transport_session)
        return self._sftp_client

    def upload_dag(self, pipeline_name, source_dir, **optional_fields):
        """
        Upload source dir into dag folder

        :param pipeline_name:
        :param source_dir:
        :param optional_fields:
        :return:
        """
        # delete previous dag folder for current dataset, as we are doing clean deployment
        self.delete_dir(
            os.path.join(self.dag_folder, f"{pipeline_name}_{optional_fields.get('env', 'dev')}_dag_out_dir"))
        # copy dag package to the airflow server
        self.put_all(f"{source_dir}/{pipeline_name}_{optional_fields.get('env', 'dev')}_dag_out_dir",
                     self.dag_folder)
        # close the connection to airflow server
        self.close_client()

    def mkdir(self, path, mode=511, ignore_existing=False):
        """
        creates the directory on remote location

        :param path: absolute path for directory
        :param mode: permissions on directory
        :param ignore_existing: whether to ignore if directory is already present
        :return: None
        """
        try:
            self.sftp_client.mkdir(path, mode)
            self.logger.info("created directory: %s", str(path).rsplit("/", maxsplit=-1)[-1])
        except IOError:
            if not ignore_existing:
                raise

    def put_all(self, localpath, remotepath):
        """
        recursively copies objects from local path to remote path

        :param localpath: localpath to copy
        :param remotepath: remotepath where to copy
        :return: None
        """
        os.chdir(os.path.split(localpath)[0])
        parent = os.path.split(localpath)[1]
        for root, _, files in os.walk(parent):
            self.mkdir(path=os.path.join(remotepath, root), ignore_existing=True)
            for file in files:
                self.sftp_client.put(os.path.join(root, file), os.path.join(remotepath, root, file))
                self.logger.info("copied file %s --> %s", file, os.path.join(remotepath, root))

    def delete_dir(self, remotepath):
        """
        deletes the directory in remote path

        :param remotepath: remotepath to delete
        :return: None
        """
        files = self.list_dir(dir_path=remotepath)
        for file in files:
            filepath = os.path.join(remotepath, file)
            if self.is_dir(filepath):
                self.delete_dir(filepath)
            else:
                self.sftp_client.remove(filepath)
        if self.is_dir(remotepath):
            self.sftp_client.rmdir(remotepath)
            self.logger.info("Removed directory %s", remotepath)
        else:
            self.logger.info("Directory %s not found on remote server", remotepath)

    def list_dir(self, dir_path):
        """
        lists the content of remote directory

        :param dir_path: path to directory
        :return: contents of directory
        """
        try:
            return self.sftp_client.listdir(path=dir_path)
        except IOError:
            return []

    def is_dir(self, path):
        """
        checks if the path is directory in remote location

        :param path: path to check
        :return: Boolean
        """
        try:
            return S_ISDIR(self.sftp_client.stat(path).st_mode)
        except IOError:
            return False

    def close_client(self):
        """
        closes the sftp client

        :return: None
        """
        self.sftp_client.close()