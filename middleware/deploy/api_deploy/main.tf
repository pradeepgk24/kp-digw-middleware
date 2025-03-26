terraform {
    backend "s3" {
  }
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 4.52.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
  # default_tags {
  #   tags = var.default_tags
  # }
}

locals {
  aws_lambda_functions = {
    format("%s%s",var.lambda_prefix,"_METADATA_API") = {
      description = "This function contains Metadata defintions APIs",
      role_arn = var.lambda_role_arn,
      memory_size = 256,
      timeout = 30,
      image_config_command = ["middleware.api.metadata.lambda_invoker_metadata_definitions.lambda_handler"],
      vpc_config = {
        security_group_ids = var.lambda_vpc_security_group_ids,
        subnet_ids = var.lambda_vpc_subnet_ids,
      },
      architectures = ["x86_64"],
      env_vars = {
        variables = {
          METADATA_CONNECTION = var.metadata_connection,
          REDIS_CONNECTION = var.redis_secret,
        }
      }
    },
        format("%s%s",var.lambda_prefix,"_SUBJECTS_API") = {
      description = "This function contains subjects API",
      role_arn = var.lambda_role_arn,
      memory_size = 512,
      timeout = 30,
      image_config_command = ["middleware.api.subjects.lambda_invoker_subjects.lambda_handler"],
      vpc_config = {
        security_group_ids = var.lambda_vpc_security_group_ids,
        subnet_ids = var.lambda_vpc_subnet_ids,
      },
      architectures = ["x86_64"],
      env_vars = {
        variables = {
          MSD_INTERNAL_API_URL = var.lambda_msd_internal_api_url,
          MSD_INTERNAL_API_SECRET = var.lambda_msd_internal_api_secret,
          METADATA_CONNECTION = var.metadata_connection,
          REDIS_CONNECTION = var.redis_secret,
        }
      }
    },
    format("%s%s",var.lambda_prefix,"_NOTIFICATIONS_API") = {
      description = "This function contains project notifications APIs",
      role_arn = var.lambda_role_arn,
      memory_size = 256,
      timeout = 30,
      image_config_command = ["middleware.api.settings.notifications.lambda_invoker_notifications.lambda_handler"],
      vpc_config = {
        security_group_ids = var.lambda_vpc_security_group_ids,
        subnet_ids = var.lambda_vpc_subnet_ids,
      },
      architectures = ["x86_64"],
      env_vars = {
        variables = {
          ENVIRONMENT = var.lambda_env,
          SUPPORTED_ENVS = var.supported_envs,
          METADATA_CONNECTION = var.metadata_connection,
          REDIS_CONNECTION = var.redis_secret,
        }
      }
    },
    format("%s%s",var.lambda_prefix,"_PIPELINES_API") = {
      description          = "This function contains pipelines APIs",
      role_arn             = var.lambda_role_arn,
      memory_size          = 2048,
      timeout              = 30,
      image_config_command = [
        "middleware.api.pipelines.lambda_invoker_pipelines.lambda_handler"
      ],
      vpc_config           = {
        security_group_ids = var.lambda_vpc_security_group_ids,
        subnet_ids         = var.lambda_vpc_subnet_ids,
      },
      architectures = ["x86_64"],
      env_vars      = {
        variables = {
          ENVIRONMENT         = var.lambda_env,
          SUPPORTED_ENVS      = var.supported_envs,
          METADATA_CONNECTION = var.metadata_connection,
          REDIS_CONNECTION = var.redis_secret,
        }
      }
    },
    format("%s%s",var.lambda_prefix,"_PIPELINES_ASYNC_API") = {
      description          = "This function contains pipelines async APIs",
      role_arn             = var.lambda_role_arn,
      memory_size          = 2048,
      timeout              = 300,
      image_config_command = [
        "middleware.api.pipelines.lambda_invoker_pipelines_async.lambda_handler"
      ],
      vpc_config           = {
        security_group_ids = var.lambda_vpc_security_group_ids,
        subnet_ids         = var.lambda_vpc_subnet_ids,
      },
      architectures = ["x86_64"],
      env_vars      = {
        variables = {
          ENVIRONMENT         = var.lambda_env,
          SUPPORTED_ENVS      = var.supported_envs,
          METADATA_CONNECTION = var.metadata_connection,
          REDIS_CONNECTION = var.redis_secret,
        }
      }
    },
    format("%s%s",var.lambda_prefix,"_WORKFLOWS_API") = {
      description          = "This function contains workflows APIs",
      role_arn             = var.lambda_role_arn,
      memory_size          = 2048,
      timeout              = 30,
      image_config_command = [
        "middleware.api.workflows.lambda_invoker_workflows.lambda_handler"
      ],
      vpc_config           = {
        security_group_ids = var.lambda_vpc_security_group_ids,
        subnet_ids         = var.lambda_vpc_subnet_ids,
      },
      architectures = ["x86_64"],
      env_vars      = {
        variables = {
          ENVIRONMENT         = var.lambda_env,
          SUPPORTED_ENVS      = var.supported_envs,
          METADATA_CONNECTION = var.metadata_connection,
          REDIS_CONNECTION = var.redis_secret,
        }
      }
    },
    format("%s%s",var.lambda_prefix,"_PIPELINE_TEMPLATES_API") = {
      description          = "This function contains pipeline templates APIs",
      role_arn             = var.lambda_role_arn,
      memory_size          = 1024,
      timeout              = 30,
      image_config_command = [
        "middleware.api.pipeline_templates.lambda_invoker_pipeline_templates.lambda_handler"
      ],
      vpc_config           = {
        security_group_ids = var.lambda_vpc_security_group_ids,
        subnet_ids         = var.lambda_vpc_subnet_ids,
      },
      architectures = ["x86_64"],
      env_vars      = {
        variables = {
          ENVIRONMENT         = var.lambda_env,
          SUPPORTED_ENVS      = var.supported_envs,
          METADATA_CONNECTION = var.metadata_connection,
          REDIS_CONNECTION = var.redis_secret,
        }
      }
    },
    format("%s%s",var.lambda_prefix,"_COMPONENTS_API") = {
      description = "This function contains components API definition",
      role_arn = var.lambda_role_arn,
      memory_size = 1024,
      timeout = 30,
      image_config_command = ["middleware.api.components.lambda_invoker_components.lambda_handler"],
      vpc_config = {
        security_group_ids = var.lambda_vpc_security_group_ids,
        subnet_ids = var.lambda_vpc_subnet_ids,
      },
      architectures = ["x86_64"],
      env_vars = {
        variables = {
          LD_LIBRARY_PATH = var.lambda_ld_library_path_to_instant_client,
          MSD_INTERNAL_API_URL = var.lambda_msd_internal_api_url,
          MSD_INTERNAL_API_SECRET = var.lambda_msd_internal_api_secret,
          METADATA_CONNECTION = var.metadata_connection,
          REDIS_CONNECTION = var.redis_secret,
        }
      }
    },
    format("%s%s",var.lambda_prefix,"_PROJECTS_SETTINGS_API") = {
      description = "This function contains projects settings API definition",
      role_arn = var.lambda_role_arn,
      memory_size = 1024,
      timeout = 30,
      image_config_command = ["middleware.api.settings.projects.lambda_invoker_projects_settings.lambda_handler"],
      vpc_config = {
        security_group_ids = var.lambda_vpc_security_group_ids,
        subnet_ids = var.lambda_vpc_subnet_ids,
      },
      architectures = ["x86_64"],
      env_vars = {
        variables = {
          METADATA_CONNECTION = var.metadata_connection,
          REDIS_CONNECTION = var.redis_secret,
          CENTRAL_RESOURCE_BUCKET = var.bucket_name
        }
      }
    },
    format("%s%s",var.lambda_prefix,"_PERMISSIONS_API") = {
      description = "This function contains security API definition",
      role_arn = var.lambda_role_arn,
      memory_size = 512,
      timeout = 30,
      image_config_command = ["middleware.api.security.lambda_invoker_permissions.lambda_handler"],
      vpc_config = {
        security_group_ids = var.lambda_vpc_security_group_ids,
        subnet_ids = var.lambda_vpc_subnet_ids,
      },
      architectures = ["x86_64"],
      env_vars = {
        variables = {
          METADATA_CONNECTION = var.metadata_connection,
          REDIS_CONNECTION = var.redis_secret,
        }
      }
    },
    format("%s%s",var.lambda_prefix,"_SECRETS_API") = {
      description = "This function contains secrets API",
      role_arn = var.lambda_role_arn,
      memory_size = 1024,
      timeout = 30,
      image_config_command = ["middleware.api.secrets.lambda_invoker_secrets.lambda_handler"],
      vpc_config = {
        security_group_ids = var.lambda_vpc_security_group_ids,
        subnet_ids = var.lambda_vpc_subnet_ids,
      },
      architectures = ["x86_64"],
      env_vars = {
        variables = {
          MSD_INTERNAL_API_URL = var.lambda_msd_internal_api_url,
          MSD_INTERNAL_API_SECRET = var.lambda_msd_internal_api_secret,
          METADATA_CONNECTION = var.metadata_connection,
          REDIS_CONNECTION = var.redis_secret,
        }
      }
    },
    format("%s%s",var.lambda_prefix,"_INFRASTRUCTURE_API") = {
      description = "This function contains infrastructure API definition",
      role_arn = var.lambda_role_arn,
      memory_size = 256,
      timeout = 30,
      image_config_command = ["middleware.api.infrastructure.lambda_invoker_infrastructure.lambda_handler"],
      vpc_config = {
        security_group_ids = var.lambda_vpc_security_group_ids,
        subnet_ids = var.lambda_vpc_subnet_ids,
      },
      architectures = ["x86_64"],
      env_vars = {
        variables = {
          MSD_INTERNAL_API_URL = var.lambda_msd_internal_api_url,
          MSD_INTERNAL_API_SECRET = var.lambda_msd_internal_api_secret,
          METADATA_CONNECTION = var.metadata_connection,
          MSD_INTERNAL_API_SG_PREFIX = var.lambda_msd_internal_api_sg_prefix
          REDIS_CONNECTION = var.redis_secret,
        }
      }
    },
    format("%s%s",var.lambda_prefix,"_EVENTS_API") = {
      description = "This function contains events APIs",
      role_arn = var.lambda_role_arn,
      memory_size = 256,
      timeout = 30,
      image_config_command = ["middleware.api.events.lambda_invoker_events.lambda_handler"],
      vpc_config = {
        security_group_ids = var.lambda_vpc_security_group_ids,
        subnet_ids = var.lambda_vpc_subnet_ids,
      },
      architectures = ["x86_64"],
      env_vars = {
        variables = {
          METADATA_CONNECTION = var.metadata_connection,
          REDIS_CONNECTION = var.redis_secret,
        }
      }
    },
    format("%s%s",var.lambda_prefix,"_LOGGING_API") = {
      description = "This function contains logging API definition",
      role_arn = var.lambda_role_arn,
      memory_size = 256,
      timeout = 30,
      image_config_command = ["middleware.api.logging.lambda_invoker_logging.lambda_handler"],
      vpc_config = {
        security_group_ids = var.lambda_vpc_security_group_ids,
        subnet_ids = var.lambda_vpc_subnet_ids,
      },
      architectures = ["x86_64"],
      env_vars = {
        variables = {
          METADATA_CONNECTION = var.metadata_connection,
          REDIS_CONNECTION = var.redis_secret
        }
      }
    },
    format("%s%s",var.lambda_prefix,"_GLOBAL_OBJECTS_API") = {
      description = "This function contains global objects API",
      role_arn = var.lambda_role_arn,
      memory_size = 1024,
      timeout = 30,
      image_config_command = ["middleware.api.global_objects.lambda_invoker_global_objects.lambda_handler"],
      vpc_config = {
        security_group_ids = var.lambda_vpc_security_group_ids,
        subnet_ids = var.lambda_vpc_subnet_ids,
      },
      architectures = ["x86_64"],
      env_vars = {
        variables = {
          METADATA_CONNECTION = var.metadata_connection,
          REDIS_CONNECTION = var.redis_secret,
        }
      }
    },
    format("%s%s",var.lambda_prefix,"_ERROR_HANDLE_API") = {
      description = "This function for error handling",
      role_arn = var.lambda_role_arn,
      memory_size = 1024,
      timeout = 30,
      image_config_command = ["middleware.api.error_handler.lambda_invoker_error_handler.lambda_handler"],
      vpc_config = {
        security_group_ids = var.lambda_vpc_security_group_ids,
        subnet_ids = var.lambda_vpc_subnet_ids,
      },
      architectures = ["x86_64"],
      env_vars = {
        variables = {
          METADATA_CONNECTION = var.metadata_connection,
          REDIS_CONNECTION = var.redis_secret,
        }
      }
    }
  }
  deployed_arn = { for func_name, extras in local.aws_lambda_functions: func_name => module.aws_lambda[func_name].deployed_lambda_arn }
  deployed_arn_name = { for func_name, extras in local.aws_lambda_functions: func_name => module.aws_lambda[func_name].deployed_lambda_arn_name }
  extra_vars = { framework_version = var.framework_version, middleware_version = var.middleware_version,
    stage_name = var.stage_name}
  template_vars = merge(local.deployed_arn, local.extra_vars)
  s3_central_packages = {
     python = {
       packages = ["nextgen-etl-pipeline-fw-code-${var.framework_version}.wheelhouse.zip", "nextgen-etl-pipeline-python-dependencies-${var.framework_version}.wheelhouse.zip", "nextgen-etl-pipeline-python-dependencies-${var.framework_version}.3-9-0.wheelhouse.zip", "nextgen-etl-pipeline-python-dependencies-${var.framework_version}-spark-databricks.zip", "nextgen-etl-pipeline-python-dependencies-${var.framework_version}-spark-glue.zip"]
     },
     python_databricks = {
       packages = ["nextgen-etl-pipeline-fw-code-${var.framework_version}.wheelhouse.zip", "nextgen-etl-pipeline-python-dependencies-${var.framework_version}.wheelhouse.zip", "nextgen-etl-pipeline-python-dependencies-${var.framework_version}.3-9-0.wheelhouse.zip", "nextgen-etl-pipeline-python-dependencies-${var.framework_version}-spark-databricks.zip", "nextgen-etl-pipeline-python-dependencies-${var.framework_version}-spark-glue.zip"]
     },
     python_databricks_submit = {
       packages = ["nextgen-etl-pipeline-fw-code-${var.framework_version}-spark.zip", "nextgen-etl-pipeline-python-dependencies-${var.framework_version}-spark-databricks.zip", "nextgen-etl-pipeline-python-dependencies-${var.framework_version}-spark-glue.zip"]
     },
     spark = {
       packages = ["nextgen-etl-pipeline-fw-code-${var.framework_version}-spark.zip", "nextgen-etl-pipeline-python-dependencies-${var.framework_version}-spark-databricks.zip", "nextgen-etl-pipeline-python-dependencies-${var.framework_version}-spark-glue.zip"]
     },
     spark_databricks = {
       packages = ["nextgen-etl-pipeline-fw-code-${var.framework_version}-spark.zip", "nextgen-etl-pipeline-python-dependencies-${var.framework_version}-spark-databricks.zip", "nextgen-etl-pipeline-python-dependencies-${var.framework_version}-spark-glue.zip"]
     },
     spark_databricks_submit = {
       packages = ["nextgen-etl-pipeline-fw-code-${var.framework_version}-spark.zip", "nextgen-etl-pipeline-python-dependencies-${var.framework_version}-spark-databricks.zip", "nextgen-etl-pipeline-python-dependencies-${var.framework_version}-spark-glue.zip"]
     },
     external_databricks = {
       packages = ["nextgen-etl-pipeline-fw-code-${var.framework_version}-spark.zip", "nextgen-etl-pipeline-python-dependencies-${var.framework_version}-spark-databricks.zip", "nextgen-etl-pipeline-python-dependencies-${var.framework_version}-spark-glue.zip"]
     },
     external_databricks_submit = {
       packages = ["nextgen-etl-pipeline-fw-code-${var.framework_version}-spark.zip", "nextgen-etl-pipeline-python-dependencies-${var.framework_version}-spark-databricks.zip", "nextgen-etl-pipeline-python-dependencies-${var.framework_version}-spark-glue.zip"]
     }
  }

}

module "s3_upload"{
   source = "./modules/s3_module"
   for_each = local.s3_central_packages
   bucket_name = var.bucket_name
   packages = each.value.packages
   job_type = each.key
}

module "s3_upload_dbx"{
   source = "./modules/s3_module"
   for_each = local.s3_central_packages
   bucket_name = var.dbx_bucket_name
   packages = each.value.packages
   job_type = each.key
}


module "aws_lambda"{
    source = "./modules/aws_lambda"

     for_each = local.aws_lambda_functions
     function_name = replace("${each.key}-${var.middleware_version}", ".", "_")
     description = each.value.description
     lambda_arn = each.value.role_arn
     memory_size = each.value.memory_size
     timeout = each.value.timeout
     image_cmd = each.value.image_config_command
     vpc_config = try(each.value.vpc_config, null)
     architecture = each.value.architectures
     environment_vars = try(each.value.env_vars, null)
     middleware_version = var.middleware_version
     ecr_registry = var.ecr_registry
     ecr_repo = var.ecr_repo
}

module "aws_lambda_invoke"{
  source = "./modules/aws_lambda_invoke"

  pipelines_async_function_arn = lookup(local.deployed_arn_name, "${format("%s%s",var.lambda_prefix,"_PIPELINES_ASYNC_API")}")
  error_function_arn = lookup(local.deployed_arn_name, "${format("%s%s",var.lambda_prefix,"_ERROR_HANDLE_API")}")
}

module "api_gateway"{
  source = "./modules/api_gateway"

  api_template_file = "./templates/api/api-gateway-specs.tftpl"
  private_vpce_ids = var.private_vpce_ids
  api_template_vars = local.template_vars
  api_name = var.api_name
  stage_name = var.stage_name
  stage_variables = var.stage_variables
  middleware_version = var.middleware_version
}


resource "aws_lambda_permission" "lambda_permission" {
  for_each = local.aws_lambda_functions

  statement_id  = "AllowNextGenAPIInvoke"
  action        = "lambda:InvokeFunction"
  function_name =  replace("${each.key}-${var.middleware_version}", ".", "_")
  principal     = "apigateway.amazonaws.com"

  # The /*/*/* part allows invocation from any stage, method and resource path
  # within API Gateway REST API.
  source_arn = "${module.api_gateway.deployment_execution_arn}*/*/*"
}

output "deployed_api_gateway" {
  value = module.api_gateway.api_url
}

