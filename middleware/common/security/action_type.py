from middleware.common.metadatabase.model.types.difw_metadb_enum import DifwMetadbEnum


class ActionType(DifwMetadbEnum):
    """
    Enum for action types
    """

    DELETE_PERMISSION = "deletePermission"
    WRITE_PERMISSION = "writePermission"
    READ_FROM_GLUE_CATALOG = "readFromGlueCatalog"
    CREATE_COMPUTE_JOB = "createComputeJob"
    DELETE_COMPUTE_JOB = "deleteComputeJob"
    EXECUTE_COMPUTE_JOB = "executeComputeJob"
    EXECUTE_PIPELINE = "executePipeline"
    DELETE_PIPELINE = "deletePipeline"
    READ_PIPELINE = "readPipeline"
    CREATE_SUBJECT = "createSubject"
    UPDATE_SUBJECT = "updateSubject"
    DELETE_SUBJECT = "deleteSubject"
    READ_SUBJECT = "readSubject"
    CREATE_PIPELINE = "createPipeline"
    UPDATE_PIPELINE = "updatePipeline"
    READ_SECRET = "readSecret"
    READ_SECRET_ITEMS = "readSecretItems"
    CREATE_SECRET = "createSecret"
    UPDATE_SECRET = "updateSecret"
    DELETE_SECRET = "deleteSecret"
    READ_PIPELINE_TEMPLATE = "readPipelineTemplate"
    CREATE_PIPELINE_TEMPLATE = "createPipelineTemplate"
    UPDATE_PIPELINE_TEMPLATE = "updatePipelineTemplate"
    DELETE_PIPELINE_TEMPLATE = "deletePipelineTemplate"
    READ_COMPONENT_TEMPLATE = "readComponentTemplate"
    CREATE_COMPONENT_TEMPLATE = "createComponentTemplate"
    UPDATE_COMPONENT_TEMPLATE = "updateComponentTemplate"
    DELETE_COMPONENT_TEMPLATE = "deleteComponentTemplate"
    ACCESS_PROJECT_SETTINGS = "accessProjectSettings"
    READ_PROJECT_SETTINGS = "readProjectSettings"
    UPDATE_PROJECT_SETTINGS = "updateProjectSettings"
    ACCESS_IAM = "accessIam"
    CREATE_NOTIFICATION = "createNotification"
    UPDATE_NOTIFICATION = "updateNotification"
    DELETE_NOTIFICATION = "deleteNotification"
    ACCESS_NOTIFICATION_SETTINGS = "accessNotificationSettings"
    WRITE_S3_OBJECTS = "writeS3Objects"
    REMOVE_S3_OBJECTS = "removeS3Objects"
    READ_PERMISSION = "readPermission"
    EXECUTE_WORKFLOW = "executeWorkflow"
    DELETE_WORKFLOW = "deleteWorkflow"
    READ_WORKFLOW = "readWorkflow"
    CREATE_WORKFLOW = "createWorkflow"
    UPDATE_WORKFLOW = "updateWorkflow"
    USE_COMPONENT = "useComponent"
    SHOW_CREATE_PIPELINE_BLANK_OPTION = "showCreatePipelineBlankOption"
    SHOW_CREATE_PIPELINE_FROM_TEMPLATE_OPTION = "showCreatePipelineFromTemplateOption"
    SHOW_CREATE_PIPELINE_FROM_YAML_OPTION = "showCreatePipelineFromYamlOption"
    CREATE_EVENT = "createEvent"

    # TODO in new version of python > 3.9 use match
    # pylint: disable=too-many-return-statements,too-many-branches
    def get_attribute_mapping(self) -> dict:
        """
        mapping of attributes you need to compare between input_permission and assigned_permissions.

        If you don't define mapping by default it return empty dict!!

        The structure of dict is the following:
        {<name_of_attr_in_input_permission>: {"attribute_name": <name_of_attr_in_assigned_permission>}
        """
        if self in [
            self.UPDATE_PIPELINE,
            self.DELETE_PIPELINE,
            self.READ_PIPELINE,
            self.EXECUTE_PIPELINE,
        ]:
            return {"pipelineName": {"attribute_name": "pipelineName"}}

        if self in [
            self.UPDATE_PIPELINE_TEMPLATE,
            self.DELETE_PIPELINE_TEMPLATE,
            self.READ_PIPELINE_TEMPLATE,
        ]:
            return {"pipelineTemplateName": {"attribute_name": "pipelineTemplateName"}}

        if self in [
            self.UPDATE_WORKFLOW,
            self.DELETE_WORKFLOW,
            self.READ_WORKFLOW,
            self.EXECUTE_WORKFLOW,
        ]:
            return {"workflowName": {"attribute_name": "workflowName"}}

        if self in [
            self.READ_FROM_GLUE_CATALOG,
        ]:
            return {"glueTables": {"attribute_name": "glueTables"},
                    "glueDatabases": {"attribute_name": "glueDatabases"}}

        if self in [
            self.CREATE_COMPUTE_JOB,
            self.DELETE_COMPUTE_JOB,
            self.EXECUTE_COMPUTE_JOB
        ]:
            return {"jobIdentifier": {"attribute_name": "jobIdentifier"}, "platform": {"attribute_name": "platform"}}

        if self in [
            self.READ_SUBJECT,
            self.UPDATE_SUBJECT,
            self.DELETE_SUBJECT
        ]:
            return {"subjectType": {"attribute_name": "subjectType"}, "subjectId": {"attribute_name": "subjectId"}}

        if self in [
            self.CREATE_SUBJECT
        ]:
            return {"subjectType": {"attribute_name": "subjectType"}}

        if self in [
            self.UPDATE_SECRET,
            self.READ_SECRET,
            self.READ_SECRET_ITEMS,
            self.DELETE_SECRET
        ]:
            return {"secretName": {"attribute_name": "secretName"}}

        if self in [
            self.READ_PROJECT_SETTINGS,
            self.UPDATE_PROJECT_SETTINGS,
        ]:
            return {"settingsType": {"attribute_name": "settingsType"}}

        if self in [
            self.CREATE_NOTIFICATION,
            self.UPDATE_NOTIFICATION,
            self.DELETE_NOTIFICATION,
        ]:
            return {"notificationType": {"attribute_name": "notificationType"}}

        if self in [
            self.WRITE_S3_OBJECTS,
        ]:
            return {"s3Bucket": {"attribute_name": "s3Bucket"}, "s3ObjectKey": {"attribute_name": "s3ObjectKey"}}

        if self in [
            self.UPDATE_COMPONENT_TEMPLATE,
            self.READ_COMPONENT_TEMPLATE,
            self.DELETE_COMPONENT_TEMPLATE
        ]:
            return {"componentTemplateName": {"attribute_name": "componentTemplateName"}}

        if self in [
            self.USE_COMPONENT,
        ]:
            return {"componentTypeName": {"attribute_name": "componentTypeName"},
                    "componentCategory": {"attribute_name": "componentCategory"}}

        # If you don't define mapping by default it return empty dict!!

        return {}