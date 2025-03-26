data "aws_ecr_image" "lambda_image" {
  repository_name = var.ecr_repo
  image_tag       = "middleware-lambda-${var.middleware_version}"
}
