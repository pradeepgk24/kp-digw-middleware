variable "bucket_name" {
  type = string
  description = "name of the bucket"
}

variable "aws_region" {
  type = string
  description = "aws region"
  default = "us-east-1"
}