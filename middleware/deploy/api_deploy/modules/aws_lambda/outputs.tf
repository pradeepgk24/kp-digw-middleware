output "deployed_lambda_arn" {
  value = aws_lambda_function.lambda_function.invoke_arn
}

output "deployed_lambda_arn_name" {
  value = aws_lambda_function.lambda_function.arn
}