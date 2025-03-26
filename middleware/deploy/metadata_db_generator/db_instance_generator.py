import json
import random
import string
import time

from middleware.deploy.metadata_db_generator.db_component_generator import DBComponentGenerator


class DBInstance(DBComponentGenerator):
    """
    Class for creation of whole instance
    """

    def generate(self, *args):
        """
        Generate new DB instance if it does not exists.

        :return:
        """
        status = self.get_database_status(self.metadb_configuration.get("dbClusterIdentifier", "difwdev-metadb-db"))
        if not status or status == 'deleting':
            self._create_new_db_instance(self.metadb_configuration.get("dbSecretManagerCredentialStorage",
                                                                       "difw-metadb-ui-credentials"))
        else:
            self.logger.warning(f'Create RDS cluster will be skipped because DB with identifier '
                                f'{self.metadb_configuration.get("dbClusterIdentifier", "difwdev-metadb-db01")} '
                                f'already exists')

    @staticmethod
    def _generate_random_password():
        """
        Method for generation of random password

        :return:
        """
        characters = list(string.ascii_letters + string.digits + "!@#$%^&*()")
        random.shuffle(characters)
        password = []
        for _ in range(10):
            password.append(random.choice(characters))
        random.shuffle(password)
        return "".join(password)

    def _save_credentials_into_sm(self, db_password, db_cluster_identifier, sm_name, tags):
        db_info = self.get_database_info(db_cluster_identifier)
        sm_data = {
            "host": db_info["Endpoint"]['Address'],
            "port": db_info["Endpoint"]['Port'],
            "user": db_info['MasterUsername'],
            "password": db_password,
            "database": self.metadb_configuration.get("databaseName", DBComponentGenerator.DATABASE_NAME)
        }
        # get credential secret
        exists_credential_secret = self.api_sm_client.get_secret(sm_name)
        # if exists_credential_secret secret does not exist,
        # create newone otherwise update existing
        if not exists_credential_secret:
            self.logger.info(f"Going to create secret with the name {sm_name}")
            self.api_sm_client.create_secrets(
                secret_name=sm_name,
                secret_string=json.dumps(sm_data, indent=2),
                tags=tags
            )
        else:
            self.logger.info(f"Going to update secret with the name {sm_name}")
            self.api_sm_client.update_secret(
                secret_name=sm_name,
                secret_string=json.dumps(sm_data, indent=2)
            )

    def _create_new_db_instance(self, secret_manager_name):
        """
        Create new instance of meta database

        :return:
        """

        db_cluster_identifier = self.metadb_configuration.get("dbClusterIdentifier", "difwdev-metadb-db01")
        # wait until DB is not deleted
        while self.get_database_status(db_cluster_identifier) == 'deleting':
            self.logger.info("Create RDS cluster wait because now it is in deletion state")
            time.sleep(15)
        tags = [
            {
                'Key': 'Application',
                'Value': 'ingest'
            },
            {
                'Key': 'Consumer',
                'Value': 'ingest-aws-dev@merck.com'
            },
            {
                'Key': 'Contact',
                'Value': 'ingest-dev-admin-role'
            },
            {
                'Key': 'Costcenter',
                'Value': '10000078'
            },
            {
                'Key': 'DataClassification',
                'Value': 'Proprietary'
            },
            {
                'Key': 'Division',
                'Value': 'CTO Org'
            },
            {
                'Key': 'Environment',
                'Value': 'Development'
            },
        ]
        db_password = DBInstance._generate_random_password()

        create_response = self.rds_client.create_db_instance(
            DBName=self.metadb_configuration.get("databaseName", DBComponentGenerator.DATABASE_NAME),
            DBInstanceIdentifier=db_cluster_identifier,
            AllocatedStorage=100,
            DBInstanceClass="db.m5.xlarge",
            Engine='postgres',
            MasterUsername='administrator',
            MasterUserPassword=db_password,
            DBSecurityGroups=self.metadb_configuration.get("dbSecurityGroups", []),
            VpcSecurityGroupIds=self.metadb_configuration.get("vpcSecurityGroups", []),
            AvailabilityZone=self.metadb_configuration.get("dbAvailabilityZone", "us-east-1a"),
            DBSubnetGroupName=self.metadb_configuration.get("dbSubnetGroupName"),
            Port=3306,
            MultiAZ=False,
            EngineVersion='15.3',
            AutoMinorVersionUpgrade=False,
            LicenseModel='postgresql-license',
            PubliclyAccessible=False,
            Tags=tags,
            StorageEncrypted=True,
            KmsKeyId=self.metadb_configuration.get("kmsKeyId", None),
            EnableCloudwatchLogsExports=[
                'postgresql', 'upgrade'
            ],
            EnablePerformanceInsights=False,
        )

        self.logger.info(f"Create RDS cluster response = {create_response}")

        # wait until DB is not created
        while self.get_database_status(db_cluster_identifier) != 'available':
            self.logger.info("Create RDS cluster wait until it will be available")
            time.sleep(15)
        self._save_credentials_into_sm(db_password, db_cluster_identifier, secret_manager_name, tags)








