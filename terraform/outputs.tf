###############################################################################
# AI Chatbot Widget — Outputs
###############################################################################

output "api_endpoint" {
  description = "API Gateway endpoint URL for the chatbot"
  value       = aws_apigatewayv2_api.main.api_endpoint
}

output "api_id" {
  description = "API Gateway ID"
  value       = aws_apigatewayv2_api.main.id
}

output "lambda_function_name" {
  description = "Lambda function name"
  value       = aws_lambda_function.chat_handler.function_name
}

output "lambda_function_arn" {
  description = "Lambda function ARN"
  value       = aws_lambda_function.chat_handler.arn
}

output "dynamodb_table_name" {
  description = "DynamoDB conversations table name"
  value       = aws_dynamodb_table.conversations.name
}

output "cloudwatch_log_group" {
  description = "Lambda CloudWatch log group name"
  value       = aws_cloudwatch_log_group.lambda.name
}

output "lambda_role_arn" {
  description = "Lambda execution role ARN"
  value       = aws_iam_role.lambda.arn
}

output "ssm_parameter_api_key" {
  description = "SSM parameter name for Anthropic API key"
  value       = aws_ssm_parameter.anthropic_api_key.name
}

output "widget_embed_code" {
  description = "Code snippet to embed the widget in a website"
  value       = <<-EOT
    <!-- Add to your HTML <head> or <body> -->
    <script>
      window.ChatWidgetConfig = {
        apiEndpoint: "${aws_apigatewayv2_api.main.api_endpoint}",
        sessionId: "user-" + Math.random().toString(36).substr(2, 9),
        title: "Chat Support",
        position: "bottom-right"
      };
    </script>
    <script src="https://your-domain.com/widget/widget.js"></script>
  EOT
}
