variable "aws_region" {
  type        = string
  description = "aws region name"
}

variable "framework_version" {
  type = string
  description = "framework_version"
}

variable "middleware_version" {
  type = string
  description = "middleware_version"
}

variable "lambda_prefix" {
  type = string
  description = "lambda prefix"
}

variable "api_name" {
  type = string
  description = "API Gateway endpoint name"
  default = "test-framework"
}

variable "stage_name" {
  description = "stage name of the API"
  type = string
  default = "dev"
}

variable "stage_variables" {
  description = "Stage variables for API gateway"
  type = map
  default = {
    LOG_LEVEL = "INFO"
  }
}

variable "lambda_role_arn" {
  description = "lambda role arn"
  type = string
}

variable "lambda_vpc_security_group_ids" {
  description = "lambda vpc security group"
  type = list(string)
}

variable "lambda_vpc_subnet_ids" {
  description = "lambda vpc subnet ids"
  type = list(string)
}

variable "lambda_env" {
  description = "aws lambda env"
  type = string
  default = "dev"
}

variable "lambda_msd_internal_api_url" {
  type = string
  description = "URL for MSD internal Active Directory API"
}

variable "lambda_msd_internal_api_sg_prefix" {
  type = string
  description = "Security group prefix for getting the security groups api call"
}

variable "lambda_msd_internal_api_secret" {
  type = string
  description = "AWS Secretmanager name which holds key for MSD internal Active Directory API"
}

variable "supported_envs" {
  description = "supported environments for resource deployment"
  type = string
  default = "dev,tst"
}

variable "bucket_name" {
  type = string
  description = "name of the bucket where dependency package will be uploaded"
}

variable "dbx_bucket_name" {
  type = string
  description = "name of the bucket where dependency package will be uploaded for dbx"
}

variable "metadata_connection" {
  type = string
  description = "Name of metadata connection"
  default = ""
}

variable "private_vpce_ids" {
  type = list
  description = "private vpce for regional configuration"
}

variable "lambda_ld_library_path_to_instant_client" {
  type = string
  description = "Connects a custom domain name with a deployed API "
  default = "/opt/oracle/lib"
}

variable "ecr_repo" {
  type = string
  description = "ecr repo where the lambda image is"
}

variable "ecr_registry" {
  type = string
  description = "ecr registry where the lambda image is"
}

variable "redis_secret" {
  type = string
  description = "redis secret variable"
}