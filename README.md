# Mortgage Application

An end-to-end mortgage application platform with loan pricing and default risk prediction APIs, containerized for cloud deployment and equipped with monitoring and CI/CD.

---

## Project Structure

```text
mortgage-application/
├── app/                # Core application code
│   ├── api/            # API endpoints (Flask)
│   ├── models/         # ML models and training scripts
│   ├── utils/          # Utility functions
│   └── config.py       # Configuration settings
├── tests/              # Unit and integration tests
├── docker/             # Docker configuration
├── kubernetes/         # Kubernetes manifests
├── monitoring/         # Prometheus & Grafana configs
├── ci-cd/              # GitHub Actions workflow
├── requirements.txt    # Python dependencies
├── .env                # Environment variables (optional)
├── README.md           # Project documentation
└── main.py             # Entry point script
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

