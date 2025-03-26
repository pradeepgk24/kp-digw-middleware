variable "function_name" {
  type = string
  description = "lambda function name"
}

variable "description" {
    type = string
    description = "description of the function"
}

variable "lambda_arn" {
  type = string
  description = "arn for lambda function"
}

variable "memory_size" {
  type = number
  description = "memory of lambda function"
}

variable "timeout" {
    type = number
    description = "timeout of lambda function"
}

variable "image_cmd" {
    type = list(string)
    description = "CMD override of Image"
}

variable "image_entrypoint" {
    type = list(string)
    description = "Entry point to the image"
    default = null
}

variable "working_directory" {
    type = string
    description = "working directory of image"
    default = ""
}

variable "environment_vars" {
    type = object({
      variables = map(string)
    })
    description = "Environment variables"
}

variable "architecture" {
  type = list(string)
  description = "Architecture of lambda function"
}

variable "vpc_config" {
  type = object({
    security_group_ids = list(string),
    subnet_ids = list(string)
  })
}

variable "ecr_repo" {
  type = string
  description = "ecr repo where the lambda image is"
}

variable "ecr_registry" {
  type = string
  description = "ecr registry where the lambda image is"
}

variable "middleware_version" {
  type = string
  description = "middleware_version"
}
