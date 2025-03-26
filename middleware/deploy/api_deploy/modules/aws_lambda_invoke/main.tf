resource "aws_lambda_function_event_invoke_config" "async_invoke_error" {
  function_name = var.pipelines_async_function_arn
  maximum_retry_attempts = 0
  destination_config {
    on_failure {
      destination = var.error_function_arn
    }
  }
}