###############################################################################
# AI Chatbot Widget — Variables
###############################################################################

variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-east-1"
}

variable "aws_profile" {
  description = "AWS CLI profile name"
  type        = string
  default     = "default"
}

variable "project_name" {
  description = "Project identifier used in resource naming"
  type        = string
  default     = "ai-chatbot-widget"
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "uat", "prod"], var.environment)
    error_message = "Environment must be dev, uat, or prod."
  }
}

variable "anthropic_api_key" {
  description = "Anthropic API key — stored encrypted in SSM Parameter Store"
  type        = string
  sensitive   = true
}

variable "anthropic_model" {
  description = "Claude model to use for chat"
  type        = string
  default     = "claude-sonnet-4-20250514"
}

variable "max_tokens" {
  description = "Maximum output tokens per response"
  type        = number
  default     = 1024
}

variable "lambda_memory" {
  description = "Lambda memory in MB"
  type        = number
  default     = 256
}

variable "lambda_timeout" {
  description = "Lambda timeout in seconds"
  type        = number
  default     = 30
}

variable "conversation_ttl_hours" {
  description = "Conversation session TTL in hours (auto-cleanup via DynamoDB TTL)"
  type        = number
  default     = 168 # 7 days

  validation {
    condition     = var.conversation_ttl_hours > 0 && var.conversation_ttl_hours <= 1440 # Max 60 days
    error_message = "TTL must be between 1 and 1440 hours."
  }
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 14
}

variable "dynamodb_billing_mode" {
  description = "DynamoDB billing mode: PAY_PER_REQUEST or PROVISIONED"
  type        = string
  default     = "PAY_PER_REQUEST"

  validation {
    condition     = contains(["PAY_PER_REQUEST", "PROVISIONED"], var.dynamodb_billing_mode)
    error_message = "Billing mode must be PAY_PER_REQUEST or PROVISIONED."
  }
}

variable "api_throttle_rate_limit" {
  description = "API Gateway throttle: requests per second"
  type        = number
  default     = 100
}

variable "api_throttle_burst_limit" {
  description = "API Gateway throttle: burst capacity"
  type        = number
  default     = 200
}
