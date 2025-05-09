# 💳 Itaú Credit Card Statement Reader

<div align="center">

![Python](https://img.shields.io/badge/python-3.13-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![CI/CD](https://github.com/brunohiperstream/itau-credit-card-statement-reader/actions/workflows/ci-cd.yml/badge.svg)
[![codecov](https://codecov.io/gh/brunohiperstream/itau-credit-card-statement-reader/branch/main/graph/badge.svg)](https://codecov.io/gh/brunohiperstream/itau-credit-card-statement-reader)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Imports: isort](https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat&labelColor=ef8336)](https://pycqa.github.io/isort/)

</div>

## 📋 Sobre o Projeto

Este projeto é um leitor automatizado de extratos de cartão de crédito do Itaú. Ele processa arquivos Excel de extratos, extrai as transações e as armazena no BigQuery para análise posterior.

### ✨ Funcionalidades

- 📥 Leitura de extratos em formato Excel
- 🔄 Processamento automático de transações
- 📊 Armazenamento no BigQuery
- 🔔 Notificações via Pub/Sub
- 🔒 Suporte a autenticação segura
- 🧪 Testes automatizados
- 🔍 Verificação de qualidade de código

## 🚀 Começando

### Pré-requisitos

- Python 3.13+
- Conta no Google Cloud Platform
- Acesso ao BigQuery e Pub/Sub
- Credenciais de serviço do GCP

### 🔧 Instalação

1. Clone o repositório:
```bash
git clone https://github.com/brunohiperstream/itau-credit-card-statement-reader.git
cd itau-credit-card-statement-reader
```

2. Crie e ative um ambiente virtual:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
.\venv\Scripts\activate  # Windows
```

3. Instale as dependências:
```bash
pip install -r requirements.txt
```

4. Configure as variáveis de ambiente:
```bash
cp .env.example .env
# Edite o arquivo .env com suas configurações
```

## 🛠️ Configuração

### Variáveis de Ambiente

Crie um arquivo `.env` na raiz do projeto com as seguintes variáveis:

```env
GCP_PROJECT_ID=seu-projeto-id
BIGQUERY_DATASET=seu-dataset
BIGQUERY_TABLE=sua-tabela
PUBSUB_SUBSCRIPTION_ID=sua-subscription
TRANSACTIONS_TOPIC=seu-topico
GOOGLE_APPLICATION_CREDENTIALS=./credentials/service-account-key.json
```

### Credenciais do Google Cloud

1. Crie uma conta de serviço no Google Cloud Console
2. Baixe a chave JSON
3. Coloque o arquivo em `credentials/service-account-key.json`

## 🧪 Testes

Execute os testes com:

```bash
pytest tests/ --cov=. --cov-report=term-missing
```

## 📦 Estrutura do Projeto

```
itau-credit-card-statement-reader/
├── finance_data_writer/
│   ├── __init__.py
│   └── writer.py
├── tests/
│   ├── resources/
│   │   └── test_extract.xlsx
│   └── unit/
│       ├── test_azul_visa_reader.py
│       └── test_writer.py
├── .env.example
├── .gitignore
├── README.md
├── requirements.txt
└── trigger.py
```

## 🔄 Fluxo de Trabalho

1. O arquivo de extrato é processado pelo `trigger.py`
2. As transações são extraídas e validadas
3. Os dados são enviados para o Pub/Sub
4. O `writer.py` recebe as mensagens e armazena no BigQuery

## 🤝 Contribuindo

1. Faça um Fork do projeto
2. Crie uma Branch para sua Feature (`git checkout -b feature/AmazingFeature`)
3. Faça o Commit das suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Faça o Push para a Branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

## 📝 Licença

Este projeto está sob a licença MIT. Veja o arquivo [LICENSE](LICENSE) para mais detalhes.

## 📫 Contato

Bruno Hiperstream - [@brunohiperstream](https://github.com/brunohiperstream)

## 🙏 Agradecimentos

- [Google Cloud Platform](https://cloud.google.com/)
- [Python](https://www.python.org/)
- [Pandas](https://pandas.pydata.org/)
- [Pytest](https://docs.pytest.org/)

---

<div align="center">
  <sub>Built with ❤️ by Bruno Hiperstream</sub>
</div>
