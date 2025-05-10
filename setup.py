from setuptools import setup, find_packages

setup(
    name="itau-credit-card-statement-reader",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "google-cloud-bigquery>=3.17.0",
        "google-cloud-pubsub>=2.19.0",
        "python-dotenv>=1.0.1",
        "pandas>=2.2.0",
        "openpyxl>=3.1.2",
        "xlrd>=2.0.1",
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