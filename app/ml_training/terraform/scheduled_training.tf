resource "aws_cloudwatch_event_rule" "weekly_training" {
  name                = "mortgage-model-weekly-training"
  description         = "Trigger model retraining weekly"
  schedule_expression = "rate(7 days)"  # Every week
}

resource "aws_cloudwatch_event_target" "lambda_target" {
  rule      = aws_cloudwatch_event_rule.weekly_training.name
  target_id = "TriggerLambda"
  arn       = aws_lambda_function.scheduled_training.arn
}

resource "aws_lambda_function" "scheduled_training" {
  filename         = "scheduled_training.zip"
  function_name    = "mortgage-scheduled-training"
  role            = aws_iam_role.lambda_training_role.arn
  handler         = "scheduled_training.lambda_handler"
  runtime         = "python3.9"
  timeout         = 900  # 15 minutes

  environment {
    variables = {
      TRAINING_SERVICE_URL = "http://model-training-service.mortgage-application.svc.cluster.local"
      SNS_TOPIC_ARN       = aws_sns_topic.model_notifications.arn
    }
  }
}