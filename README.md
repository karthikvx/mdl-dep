# Mortgage Application

This architecture uses AWS managed services to create a scalable, resilient, and decoupled system.


![Architecture](/assets/mortgage_loan_process.png)


---

### Key Architecture Components Explained:

1.  **Event-Driven Core (AWS EventBridge):** The central nervous system. A loan application event is published to the Event Bus. EventBridge then fans out this event to the two independent microservices simultaneously, ensuring decoupling and scalability.

2.  **Microservices (Deployed on EKS/ECS):**
    *   **Loan Pricing Service:** A containerized service that listens for events. It calculates the rate, potentially using parameters from a fast database like **DynamoDB**. It emits a "PricingResult" event.
    *   **Default Prediction Service:** Another containerized service. It loads a pre-trained **Random Forest model** from an S3 bucket to make a risk prediction on the same loan event. It emits a "RiskResult" event.

3.  **Data Aggregation (AWS Lambda):** A serverless function acts as a consumer. It listens for the result events from both services, aggregates the pricing and risk data, and stores the final result in a **DynamoDB** table for the front-end to retrieve.

4.  **Monitoring Stack:**
    *   **Prometheus:** Scrapes metrics (e.g., request latency, error rates, model prediction times) exposed by each microservice.
    *   **Grafana:** Queries Prometheus to create real-time dashboards for operational visibility (e.g., loans processed per minute, average response time).

5.  **CI/CD Pipeline (GitHub Actions):** Automates the entire deployment process:
    *   On a code push, it builds a new Docker image.
    *   Runs tests and security scans.
    *   Pushes the image to **Amazon ECR** (Container Registry).
    *   Updates the deployment on **Amazon EKS** (Kubernetes Service) to roll out the new version.

This architecture allows each component to scale independently, provides resilience if one service fails, and enables real-time monitoring of the entire system.



# Mortgage Application POC

An end-to-end mortgage application platform with loan pricing and default risk prediction APIs, containerized for cloud deployment and equipped with monitoring and CI/CD.

---

## Project Structure

```text
mortgage-application/
├── main.py 
├── main_orchestrator.py                 # Entry point for orchestrator service
├── main_pricing.py                      # Entry point for pricing service  
├── main_prediction.py                   # Entry point for prediction service
├── app/
│   ├── __init__.py
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py                    # 1. SHARED MODELS AND EVENTS
│   ├── services/
│   │   ├── __init__.py
│   │   ├── event_publisher.py            # 2. AWS EVENT PUBLISHER
│   │   ├── pricing_service.py            # 3. LOAN PRICING MICROSERVICE
│   │   ├── prediction_service.py         # 4. DEFAULT PREDICTION MICROSERVICE
│   │   └── orchestrator.py               # 6. MAIN APPLICATION ORCHESTRATOR
│   ├── lambda/
│   │   ├── __init__.py
│   │   └── aggregation_handler.py        # 5. DATA AGGREGATION LAMBDA
│   └── utils/
│       ├── __init__.py
│       └── test_data.py                  # 7. SAMPLE USAGE AND TESTING
├── docker/
│   └── Dockerfile
    ├── Dockerfile.orchestrator          # References main_orchestrator.py
    ├── Dockerfile.pricing               # References main_pricing.py
    └── Dockerfile.prediction            # References main_prediction.py
├── kubernetes/
│   ├── namespace.yaml
│   ├── loan-pricing-service.yaml
│   ├── default-prediction-service.yaml
│   ├── mortgage-orchestrator.yaml
│   └── rbac.yaml
├── monitoring/
│   ├── prometheus/
│   │   └── prometheus.yml
│   └── grafana/
│       └── dashboards/
│           └── mortgage-app-dashboard.json
├── ci-cd/
│   └── .github/
│       └── workflows/
│           └── deploy.yml
├── infrastructure/
│   ├── terraform/
│   │   ├── main.tf
│   │   ├── eventbridge.tf
│   │   ├── dynamodb.tf
│   │   └── s3.tf
│   └── cloudformation/
│       └── mortgage-app-stack.yaml
├── tests/
│   ├── __init__.py
│   ├── unit/
│   │   ├── test_pricing_service.py
│   │   ├── test_prediction_service.py
│   │   └── test_orchestrator.py
│   └── integration/
│       └── test_end_to_end.py
├── scripts/
│   ├── setup_environment.sh
│   ├── deploy_services.sh
│   └── load_test_data.py
├── requirements.txt
├── requirements-dev.txt
├── .env.example
├── docker-compose.yml
└── README.md
```

## Directory Details

- **app/**: Core application code
  - **api/**: Flask endpoints for loan pricing and default prediction
  - **models/**: ML model training and serialized models
  - **utils/**: Loan calculations and data preprocessing
  - **config.py**: Centralized configuration (API keys, DB URLs, etc.)
- **tests/**: Unit and integration tests for all modules
- **docker/**: Dockerfile for containerization
- **kubernetes/**: YAML files for Kubernetes deployment
- **monitoring/**: Prometheus config and Grafana dashboards
- **ci-cd/**: GitHub Actions workflow for CI/CD
- **requirements.txt**: Python dependencies
- **.env**: Environment variables (not committed)
- **main.py**: Application entry point

## Features & Workflow

- **Loan Pricing**: Calculates interest rates based on loan amount, credit score, and DTI ratio
- **Default Prediction**: Predicts default risk using a Random Forest model
- **Deployment**: Containerized with Docker, deployable to Kubernetes
- **Monitoring**: Prometheus for metrics, Grafana for visualization
- **CI/CD**: Automated pipeline with GitHub Actions

## Setup & Usage

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```
2. **Run the application**
   ```bash
   python main.py
   ```
3. **Run tests**
   ```bash
   pytest tests/
   ```
4. **Build Docker image**
   ```bash
   docker build -t mortgage-app ./docker
   ```
5. **Deploy to Kubernetes**
   - Apply manifests in `kubernetes/`

## Example API Requests

**Price a loan:**
```bash
curl -X POST http://localhost:5000/price_loan \
  -H "Content-Type: application/json" \
  -d '{"loan_amount": 200000, "credit_score": 720, "dti_ratio": 0.35}'
```

**Predict default risk:**
```bash
curl -X POST http://localhost:5000/predict_default \
  -H "Content-Type: application/json" \
  -d '{"loan_amount": 200000, "credit_score": 720, "dti_ratio": 0.35}'
```

## License

MIT License. See [LICENSE](LICENSE) for details.

