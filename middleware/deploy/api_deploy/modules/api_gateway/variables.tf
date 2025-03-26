variable "api_name" {
  description = "API Gateway endpoint name"
}

variable "api_template_file" {
  description = "API Gateway OpenAPI 3 template file"
}

variable "api_template_vars" {
  description = "Variables required in the OpenAPI template file"
  type        = map
}

variable "stage_name" {
  type = string
  description = "stage name of the API"
}

variable "stage_variables" {
  type = map
  description = "stage_variables"
}

variable "private_vpce_ids" {
  type = list
  description = "private vpce for regional configuration"
}

variable "middleware_version" {
  type = string
  description = "middleware_version"
}