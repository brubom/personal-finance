from setuptools import setup, find_packages

setup(
    name="itau-credit-card-statement-reader",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "google-cloud-bigquery>=3.17.0",
        "google-cloud-pubsub>=2.19.0",
        "google-cloud-storage>=2.14.0",
        "python-dotenv>=1.0.1",
        "pandas>=2.2.0",
        "openpyxl>=3.1.2",
        "xlrd>=2.0.1",
        "python-json-logger>=2.0.7",
        "opentelemetry-api>=1.23.0",
        "opentelemetry-sdk>=1.23.0",
        "opentelemetry-exporter-gcp-trace>=1.9.0",
        "functions-framework==3.8.2",
    ],
    extras_require={
        "dev": [
            "pytest>=8.0.0",
            "pytest-cov>=4.1.0",
            "flake8>=7.0.0",
            "black>=24.1.0",
            "isort>=5.13.0",
            "mypy>=1.8.0",
            "bandit>=1.7.7",
            "safety>=2.3.5",
        ],
    },
    python_requires=">=3.13",
) 