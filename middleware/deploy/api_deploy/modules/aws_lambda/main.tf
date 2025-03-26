resource "aws_lambda_function" "lambda_function" {
    function_name = var.function_name
    description = var.description
    role = var.lambda_arn
    image_uri = "${var.ecr_registry}/${var.ecr_repo}@${data.aws_ecr_image.lambda_image.image_digest}"
    memory_size = var.memory_size
    package_type = "Image"
    timeout = var.timeout
    image_config {
      command = var.image_cmd
      entry_point = var.image_entrypoint
      working_directory = var.working_directory
    }
    architectures = var.architecture
    dynamic "vpc_config" {
      for_each = var.vpc_config[*]
      content {
        security_group_ids = vpc_config.value.security_group_ids
        subnet_ids = vpc_config.value.subnet_ids
      }
    }
    dynamic "environment" {
      for_each = var.environment_vars[*]
      content {
        variables = environment.value.variables
      }
    }
}