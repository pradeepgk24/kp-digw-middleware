locals {
    api_url = "${aws_api_gateway_deployment._.invoke_url}${aws_api_gateway_stage._.stage_name}"
    vpces = { PRIVATE_VPCE_IDS = var.private_vpce_ids }
    template_vars = merge(local.vpces, var.api_template_vars)
}

resource "aws_api_gateway_account" "api" {
  cloudwatch_role_arn = aws_iam_role.cloudwatch.arn
}

resource "aws_iam_role" "cloudwatch" {
  name               = "${var.api_name}-${var.middleware_version}-api-gw-iam-role"
  assume_role_policy = data.aws_iam_policy_document.assume_role.json
}

resource "aws_iam_role_policy" "cloudwatch" {
  name   = "${var.api_name}-${var.middleware_version}-api-gw-iam-role-policy"
  role   = aws_iam_role.cloudwatch.id
  policy = data.aws_iam_policy_document.cloudwatch.json
}

resource "aws_api_gateway_rest_api" "_" {
  name           = var.api_name

  body = templatefile(var.api_template_file, local.template_vars)

  put_rest_api_mode = "merge"

  endpoint_configuration {
    types = ["PRIVATE"]
  }
}

resource "aws_api_gateway_rest_api_policy" "_" {
  rest_api_id = aws_api_gateway_rest_api._.id

  policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": "*",
      "Action": "execute-api:Invoke",
      "Resource": "${aws_api_gateway_rest_api._.execution_arn}/*"
    }
  ]
}
EOF
}

resource "aws_api_gateway_deployment" "_" {
  rest_api_id = aws_api_gateway_rest_api._.id

  triggers = {
    redeployment = sha1(jsonencode(aws_api_gateway_rest_api._.body))
  }

  lifecycle {
    create_before_destroy = true
  }

  depends_on = [
       aws_api_gateway_rest_api_policy._
  ]
}

resource "aws_api_gateway_stage" "_" {
  depends_on = [aws_cloudwatch_log_group.api-gw-stage]
  stage_name    = var.stage_name
  rest_api_id   = aws_api_gateway_rest_api._.id
  deployment_id = aws_api_gateway_deployment._.id
  variables = var.stage_variables

    access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api-gw-stage.arn
    format          = "{ \"requestId\":\"$context.requestId\", \"ip\": \"$context.identity.sourceIp\", \"requestTime\":\"$context.requestTime\", \"httpMethod\":\"$context.httpMethod\",\"status\":$context.status, \"integrationRequestId\": \"$context.integration.requestId\", \"functionResponseStatus\": \"$context.integration.status\", \"path\": \"$context.path\" }"
    }
}

resource "aws_cloudwatch_log_group" "api-gw-stage" {
  name = "API-Gateway-Execution-Logs_${aws_api_gateway_rest_api._.id}/${var.stage_name}"
}