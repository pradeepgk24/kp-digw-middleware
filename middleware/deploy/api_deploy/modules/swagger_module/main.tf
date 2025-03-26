terraform {
  backend "s3" { }
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 4.52.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

locals {
  swagger_doc_path = "../../../../../documentation/api-docs/swagger"
  mime_types       = {
    yml  = "text/yaml"
    htm  = "text/html"
    html = "text/html"
    css  = "text/css"
    ttf  = "font/ttf"
    js   = "application/javascript"
    map  = "application/javascript"
    json = "application/json"
    svg   = "image/svg+xml"
    ico   = "image/x-icon"
    png   = "image/png"
  }
}

resource "aws_s3_object" "_" {
  for_each     = fileset(local.swagger_doc_path, "**/*.*")
  bucket       = var.bucket_name
  key          = each.value
  source       = "${local.swagger_doc_path}/${each.value}"
  etag         = filemd5("${local.swagger_doc_path}/${each.value}")
  content_type = lookup(local.mime_types, split(".", each.value)[length(split(".", each.value)) - 1])
}

