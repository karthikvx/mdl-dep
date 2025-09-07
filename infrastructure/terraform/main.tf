provider "aws" {
  region = var.aws_region
}

# VPC and Networking
resource "aws_vpc" "mortgage_vpc" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true
  
  tags = {
    Name = "mortgage-application-vpc"
  }
}

# EKS Cluster
resource "aws_eks_cluster" "mortgage_cluster" {
  name     = "mortgage-application-cluster"
  role_arn = aws_iam_role.eks_cluster_role.arn
  version  = "1.27"

  vpc_config {
    subnet_ids = [
      aws_subnet.private_subnet_1.id,
      aws_subnet.private_subnet_2.id,
      aws_subnet.public_subnet_1.id,
      aws_subnet.public_subnet_2.id
    ]
    endpoint_private_access = true
    endpoint_public_access  = true
  }

  depends_on = [
    aws_iam_role_policy_attachment.eks_cluster_policy,
  ]
}

# EventBridge Custom Bus
resource "aws_cloudwatch_event_bus" "mortgage_bus" {
  name = "mortgage-application-bus"
  
  tags = {
    Environment = "production"
    Application = "mortgage-app"
  }
}

# DynamoDB Tables
resource "aws_dynamodb_table" "loan_results" {
  name           = "loan-application-results"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "application_id"

  attribute {
    name = "application_id"
    type = "S"
  }

  tags = {
    Name = "LoanApplicationResults"
  }
}

resource "aws_dynamodb_table" "pricing_parameters" {
  name           = "loan-pricing-parameters"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "parameter_type"

  attribute {
    name = "parameter_type"
    type = "S"
  }
}

# S3 Bucket for ML Models
resource "aws_s3_bucket" "ml_models" {
  bucket = "mortgage-ml-models-${random_id.bucket_suffix.hex}"
}

resource "random_id" "bucket_suffix" {
  byte_length = 4
}

# ECR Repositories
resource "aws_ecr_repository" "pricing_service" {
  name = "mortgage-app/pricing-service"
}

resource "aws_ecr_repository" "prediction_service" {
  name = "mortgage-app/prediction-service"
}

resource "aws_ecr_repository" "orchestrator_service" {
  name = "mortgage-app/orchestrator-service"
}

# Lambda Function for Data Aggregation
resource "aws_lambda_function" "data_aggregator" {
  filename         = "lambda_deployment.zip"
  function_name    = "mortgage-data-aggregator"
  role            = aws_iam_role.lambda_role.arn
  handler         = "aggregation_handler.lambda_handler"
  runtime         = "python3.9"
  timeout         = 30

  environment {
    variables = {
      RESULTS_TABLE = aws_dynamodb_table.loan_results.name
    }
  }
}

# EventBridge Rules
resource "aws_cloudwatch_event_rule" "pricing_result_rule" {
  name           = "pricing-result-rule"
  event_bus_name = aws_cloudwatch_event_bus.mortgage_bus.name

  event_pattern = jsonencode({
    source      = ["loan-pricing-service"]
    detail-type = ["PricingResult"]
  })
}

resource "aws_cloudwatch_event_rule" "risk_result_rule" {
  name           = "risk-result-rule"
  event_bus_name = aws_cloudwatch_event_bus.mortgage_bus.name

  event_pattern = jsonencode({
    source      = ["default-prediction-service"]
    detail-type = ["RiskResult"]
  })
}

# EventBridge Targets
resource "aws_cloudwatch_event_target" "lambda_target_pricing" {
  rule           = aws_cloudwatch_event_rule.pricing_result_rule.name
  event_bus_name = aws_cloudwatch_event_bus.mortgage_bus.name
  target_id      = "PricingResultTarget"
  arn            = aws_lambda_function.data_aggregator.arn
}

resource "aws_cloudwatch_event_target" "lambda_target_risk" {
  rule           = aws_cloudwatch_event_rule.risk_result_rule.name
  event_bus_name = aws_cloudwatch_event_bus.mortgage_bus.name
  target_id      = "RiskResultTarget"
  arn            = aws_lambda_function.data_aggregator.arn
}
