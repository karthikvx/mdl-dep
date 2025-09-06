## Deployment Scripts Overview
# 1. Core Deployment Scripts

setup-env.sh - Initial environment setup (AWS resources, K8s namespace, monitoring)
build-images.sh - Automated Docker image building and ECR pushing
deploy.sh - Main deployment orchestration with health checks
rollback.sh - Safe rollback to previous versions
cleanup.sh - Complete resource cleanup

# 2. Development Tools

dev-scripts.sh - Interactive development helpers with menu system
CI/CD Pipeline - GitHub Actions workflow for automated testing and deployment

## Key Features
Automated Infrastructure Setup

ECR repository creation
EventBridge custom bus setup
DynamoDB table provisioning
S3 bucket for ML models
Kubernetes secrets management

Deployment Orchestration

Sequential service deployment with dependency management
Health check verification
Monitoring integration
Network policy application

Development Experience

Port forwarding for local development
Integrated log streaming
Automated integration testing
Resource monitoring dashboard

Production Ready

Blue-green deployment support via image tags
Automated rollback capabilities
Resource cleanup with confirmation prompts
CI/CD pipeline with testing and coverage

Quick Start
bash# 
1. Set up environment
./setup-env.sh

# 2. Build and push images
./build-images.sh latest

# 3. Deploy application
./deploy.sh staging

# 4. Development helpers
./dev-scripts.sh

The scripts handle the complete deployment lifecycle of event-driven mortgage application, from initial setup through production deployment and maintenance. They integrate seamlessly with your existing Docker, Kubernetes, and AWS infrastructure while providing comprehensive monitoring and development tools.
