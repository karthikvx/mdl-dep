from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="mortgage-ml-application",
    version="1.0.0",
    author="Your Organization",
    author_email="dev@yourorg.com",
    description="Event-driven distributed mortgage application with ML capabilities",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourorg/mortgage-ml-app",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Financial and Insurance Industry",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "mortgage-orchestrator=main:run_orchestrator",
            "mortgage-pricing=main:run_pricing",
            "mortgage-prediction=main:run_prediction",
            "mortgage-training=main:run_model_training",
            "mortgage-dashboard=main:run_dashboard",
        ],
    },
    extras_require={
        "dev": [
            "pytest>=7.4.3",
            "pytest-flask>=1.3.0",
            "pytest-mock>=3.12.0",
            "pytest-cov>=4.1.0",
            "black>=23.12.0",
            "flake8>=6.1.0",
            "isort>=5.13.2",
            "mypy>=1.8.0",
            "moto>=4.2.14",
        ],
        "production": [
            "gunicorn>=21.2.0",
            "redis>=5.0.1",
            "celery>=5.3.4",
        ]
    }
)