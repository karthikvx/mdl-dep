# ===============================================
# 1. INFRASTRUCTURE SETUP (Terraform)
# ===============================================

# File: infrastructure/terraform/main.tf
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

---
# ===============================================
# 2. CI/CD PIPELINE (GitHub Actions)
# ===============================================

# File: .github/workflows/deploy.yml
name: Deploy Mortgage Application

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

env:
  AWS_REGION: us-west-2
  EKS_CLUSTER_NAME: mortgage-application-cluster

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.9'
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pytest pytest-cov
    
    - name: Run tests
      run: |
        pytest tests/ --cov=app --cov-report=xml
    
    - name: Upload coverage reports
      uses: codecov/codecov-action@v3

  security-scan:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    
    - name: Run Trivy vulnerability scanner
      uses: aquasecurity/trivy-action@master
      with:
        scan-type: 'fs'
        scan-ref: '.'

  build-and-push:
    needs: [test, security-scan]
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Configure AWS credentials
      uses: aws-actions/configure-aws-credentials@v2
      with:
        aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
        aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        aws-region: ${{ env.AWS_REGION }}
    
    - name: Login to Amazon ECR
      id: login-ecr
      uses: aws-actions/amazon-ecr-login@v1
    
    - name: Build and push Docker images
      env:
        ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
        IMAGE_TAG: ${{ github.sha }}
      run: |
        # Build pricing service
        docker build -f docker/Dockerfile.pricing -t $ECR_REGISTRY/mortgage-app/pricing-service:$IMAGE_TAG .
        docker push $ECR_REGISTRY/mortgage-app/pricing-service:$IMAGE_TAG
        
        # Build prediction service
        docker build -f docker/Dockerfile.prediction -t $ECR_REGISTRY/mortgage-app/prediction-service:$IMAGE_TAG .
        docker push $ECR_REGISTRY/mortgage-app/prediction-service:$IMAGE_TAG
        
        # Build orchestrator service
        docker build -f docker/Dockerfile.orchestrator -t $ECR_REGISTRY/mortgage-app/orchestrator-service:$IMAGE_TAG .
        docker push $ECR_REGISTRY/mortgage-app/orchestrator-service:$IMAGE_TAG

  deploy:
    needs: build-and-push
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Configure AWS credentials
      uses: aws-actions/configure-aws-credentials@v2
      with:
        aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
        aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        aws-region: ${{ env.AWS_REGION }}
    
    - name: Update kubeconfig
      run: |
        aws eks update-kubeconfig --region ${{ env.AWS_REGION }} --name ${{ env.EKS_CLUSTER_NAME }}
    
    - name: Deploy to EKS
      env:
        IMAGE_TAG: ${{ github.sha }}
        ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
      run: |
        # Update image tags in Kubernetes manifests
        sed -i "s|IMAGE_TAG|$IMAGE_TAG|g" kubernetes/*.yaml
        sed -i "s|ECR_REGISTRY|$ECR_REGISTRY|g" kubernetes/*.yaml
        
        # Apply Kubernetes manifests
        kubectl apply -f kubernetes/namespace.yaml
        kubectl apply -f kubernetes/rbac.yaml
        kubectl apply -f kubernetes/pricing-service.yaml
        kubectl apply -f kubernetes/prediction-service.yaml
        kubectl apply -f kubernetes/orchestrator.yaml
        
        # Wait for deployments to be ready
        kubectl rollout status deployment/loan-pricing-service -n mortgage-application
        kubectl rollout status deployment/default-prediction-service -n mortgage-application
        kubectl rollout status deployment/mortgage-orchestrator -n mortgage-application

---
# ===============================================
# 3. DEPLOYMENT PROCESS STEPS
# ===============================================

# Step 1: Infrastructure Provisioning
terraform init
terraform plan -var-file="production.tfvars"
terraform apply -var-file="production.tfvars"

# Step 2: Upload ML Model to S3
aws s3 cp models/random_forest_model.pkl s3://mortgage-ml-models-xyz/random_forest_default_model.pkl

# Step 3: Populate DynamoDB with Initial Data
aws dynamodb put-item --table-name loan-pricing-parameters --item '{
  "parameter_type": {"S": "base_rate"},
  "value": {"N": "4.5"},
  "last_updated": {"S": "2024-01-01T00:00:00Z"}
}'

# Step 4: Build and Push Docker Images
docker build -f docker/Dockerfile -t mortgage-app/pricing-service --build-arg SERVICE_TYPE=pricing .
docker build -f docker/Dockerfile -t mortgage-app/prediction-service --build-arg SERVICE_TYPE=prediction .
docker build -f docker/Dockerfile -t mortgage-app/orchestrator --build-arg SERVICE_TYPE=orchestrator .

# Tag and push to ECR
docker tag mortgage-app/pricing-service:latest 123456789012.dkr.ecr.us-west-2.amazonaws.com/mortgage-app/pricing-service:latest
docker push 123456789012.dkr.ecr.us-west-2.amazonaws.com/mortgage-app/pricing-service:latest

# Step 5: Deploy to EKS
kubectl apply -f kubernetes/

# Step 6: Verify Deployments
kubectl get pods -n mortgage-application
kubectl get services -n mortgage-application
kubectl logs -f deployment/loan-pricing-service -n mortgage-application

---
# ===============================================
# 4. MONITORING SETUP
# ===============================================

# File: monitoring/prometheus/values.yaml
prometheus:
  prometheusSpec:
    additionalScrapeConfigs:
    - job_name: 'mortgage-app-services'
      kubernetes_sd_configs:
      - role: pod
        namespaces:
          names:
          - mortgage-application
      relabel_configs:
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
        action: keep
        regex: true
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_path]
        action: replace
        target_label: __metrics_path__
        regex: (.+)

# Install Prometheus using Helm
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
helm install prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring --create-namespace \
  --values monitoring/prometheus/values.yaml

---
# ===============================================
# 5. WHAT HAPPENS DURING DEPLOYMENT
# ===============================================

# Phase 1: Infrastructure Creation
- VPC with public/private subnets created
- EKS cluster provisioned with managed node groups
- EventBridge custom bus "mortgage-application-bus" created
- DynamoDB tables created for storing results and parameters
- S3 bucket created for ML model storage
- ECR repositories created for container images
- Lambda function deployed for data aggregation
- EventBridge rules configured to trigger Lambda on events
- IAM roles and policies created with least-privilege access

# Phase 2: Application Build
- Code tested with pytest and coverage reports
- Security scanning with Trivy
- Docker images built for each microservice
- Images tagged with commit SHA for versioning
- Images pushed to ECR repositories

# Phase 3: Kubernetes Deployment
- Namespace "mortgage-application" created
- Service accounts and RBAC policies applied
- Deployments created with 3 replicas each for high availability
- Services exposed internally within cluster
- Load balancer created for orchestrator (external access)
- Health checks configured for all pods
- Resource limits set for CPU/memory

# Phase 4: Event-Driven Architecture Activation
- EventBridge starts routing events between services
- Lambda function begins processing aggregation events
- Prometheus starts scraping metrics from all services
- Application becomes fully operational

# Phase 5: Monitoring and Observability
- Grafana dashboards display real-time metrics
- CloudWatch logs capture application events
- AWS X-Ray provides distributed tracing
- Health checks ensure service availability

---
# ===============================================
# 6. TRAFFIC FLOW IN AWS
# ===============================================

# Request Flow:
1. Client → ALB → EKS Orchestrator Service
2. Orchestrator → Publishes LoanApplicationSubmitted to EventBridge
3. EventBridge → Routes to Pricing & Prediction services simultaneously
4. Pricing Service → Calculates rate → Publishes PricingResult to EventBridge
5. Prediction Service → ML prediction → Publishes RiskResult to EventBridge
6. EventBridge → Triggers Lambda for both result types
7. Lambda → Aggregates results in DynamoDB
8. Lambda → Makes final decision → Updates DynamoDB
9. Client → Polls orchestrator for results

# Data Storage:
- DynamoDB: Application results, pricing parameters
- S3: ML models, logs, backups
- ECR: Container images

# Monitoring Data Flow:
- Prometheus scrapes metrics from all pods
- Grafana queries Prometheus for dashboards
- CloudWatch receives application logs
- AWS X-Ray traces requests across services

---
# ===============================================
# 7. SCALING AND RESILIENCE
# ===============================================

# Horizontal Pod Autoscaler
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: pricing-service-hpa
  namespace: mortgage-application
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: loan-pricing-service
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70

# Cluster Autoscaler for EKS nodes
# Circuit breaker pattern in services
# Multi-AZ deployment for high availability
# DynamoDB auto-scaling based on demand
# EventBridge automatic retry with dead letter queues

---
# ===============================================
# 8. COST OPTIMIZATION
# ===============================================

# EKS: Use Spot instances for non-critical workloads
# DynamoDB: Pay-per-request billing model
# Lambda: Only pay for actual execution time
# S3: Use Intelligent Tiering for model storage
# EventBridge: Pay per event (very low cost)
# ECR: Repository storage costs minimal


#=========================

When deploying this event-driven mortgage application to AWS, here's what happens step by step:## Summary: What Happens During AWS Deployment

When you deploy this event-driven mortgage application to AWS, here's the complete flow:

### **1. Infrastructure Setup (15-30 minutes)**
- **EKS Cluster**: Creates managed Kubernetes cluster with auto-scaling node groups
- **EventBridge**: Sets up custom event bus for service communication
- **DynamoDB**: Creates tables for storing loan results and pricing parameters
- **Lambda**: Deploys data aggregation function that triggers on EventBridge events
- **ECR**: Creates container registries for your Docker images
- **VPC/Networking**: Sets up secure network with public/private subnets

### **2. CI/CD Pipeline Execution (5-10 minutes)**
- **Testing**: Runs pytest and security scans
- **Docker Build**: Creates separate images for each microservice
- **ECR Push**: Uploads images to AWS container registry
- **Kubernetes Deploy**: Updates EKS with new pod configurations

### **3. Runtime Architecture**
```
Internet → ALB → EKS Orchestrator → EventBridge → [Pricing + Prediction Services]
                                       ↓
                                   Lambda Aggregator → DynamoDB
```

### **4. Live Traffic Flow**
1. **Client Request** → Load Balancer → Orchestrator Service (EKS Pod)
2. **Event Publishing** → Orchestrator publishes to EventBridge custom bus
3. **Parallel Processing** → EventBridge routes to Pricing + Prediction services simultaneously
4. **Result Events** → Each service publishes results back to EventBridge
5. **Data Aggregation** → Lambda function combines results in DynamoDB
6. **Response** → Client retrieves final decision from orchestrator

### **5. Auto-Scaling & Resilience**
- **Pod Auto-scaling**: Based on CPU/memory usage (3-10 replicas per service)
- **Node Auto-scaling**: EKS adds/removes EC2 instances based on demand
- **Event Retry**: EventBridge automatically retries failed events
- **Health Checks**: Kubernetes restarts unhealthy pods automatically

### **6. Monitoring & Observability**
- **Prometheus**: Scrapes metrics from all services
- **Grafana**: Displays real-time dashboards
- **CloudWatch**: Captures application logs
- **AWS X-Ray**: Provides distributed tracing across services

### **7. Cost Structure**
- **EKS**: ~$0.10/hour for cluster + EC2 instance costs
- **Lambda**: Pay-per-execution (very low for aggregation)
- **DynamoDB**: Pay-per-request model
- **EventBridge**: ~$1 per million events
- **Total estimated cost**: $200-500/month depending on traffic

The beauty of this architecture is that each component scales independently, provides high availability, and follows AWS best practices for microservices deployment.