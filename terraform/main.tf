##################################################
# main.tf - Revisado
##################################################
terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 4.0"
    }
  }
  required_version = ">= 1.3.0"
}

provider "google" {
  project = var.project_id
  region  = var.region
}

#############################
# 1) BUCKETS
#############################

resource "google_storage_bucket" "functions_code_bucket" {
  name     = "${var.project_id}-functions-code"
  location = var.region
}

resource "google_storage_bucket" "data_bucket" {
  name     = "${var.project_id}-data-bucket"
  location = var.region
}

#############################
# 2) PUB/SUB + ASSINATIVA p/ BigQuery
#############################

resource "google_pubsub_topic" "personal_finance_flow" {
  name = "personal_finance_flow"
}

resource "google_bigquery_dataset" "personal_finance" {
  dataset_id                  = "personal_finance"
  project                     = var.project_id
  location                    = var.location
  friendly_name               = "Personal Finance Dataset"
  description                 = "Dataset para armazenar transações financeiras"
  default_table_expiration_ms = null
}

resource "google_bigquery_table" "personal_finance_flow" {
  dataset_id = google_bigquery_dataset.personal_finance.dataset_id
  table_id   = "personal_finance_flow"

  schema = <<EOF
[
  {"name":"id",          "type":"STRING", "mode":"NULLABLE"},
  {"name":"date",        "type":"DATE",   "mode":"NULLABLE"},
  {"name":"value",       "type":"FLOAT",  "mode":"NULLABLE"},
  {"name":"description", "type":"STRING", "mode":"NULLABLE"},
  {"name":"account",     "type":"STRING", "mode":"NULLABLE"}
]
EOF

  time_partitioning {
    type  = "DAY"
    field = "date"
  }
}

resource "google_pubsub_subscription" "finance_to_bq" {
  name  = "finance-to-bq"
  topic = google_pubsub_topic.personal_finance_flow.name

  bigquery_config {
    table            = google_bigquery_table.personal_finance_flow.id
    use_topic_schema = true
    write_metadata   = true
  }

  ack_deadline_seconds       = 10
  message_retention_duration = "604800s"  # 7 dias
}

#############################
# 3) CLOUD FUNCTIONS
#############################

# (A) function_file_arrival (Storage Trigger)
data "archive_file" "function_file_arrival" {
  type        = "zip"
  source_dir  = "${path.module}/../function_file_arrival"
  output_path = "${path.module}/function_file_arrival.zip"
}

resource "google_storage_bucket_object" "function_file_arrival_zip" {
  name   = "function_file_arrival.zip"
  bucket = google_storage_bucket.functions_code_bucket.name
  source = data.archive_file.function_file_arrival.output_path
}

resource "google_cloudfunctions_function" "function_file_arrival" {
  name        = "function_file_arrival"
  runtime     = "python39"
  entry_point = "storage_trigger_function"
  project     = var.project_id
  region      = var.region

  source_archive_bucket = google_storage_bucket.functions_code_bucket.name
  source_archive_object = google_storage_bucket_object.function_file_arrival_zip.name

  # Gatilho de Storage
  event_trigger {
    event_type = "google.storage.object.finalize"
    resource   = google_storage_bucket.data_bucket.name
  }

  # Esta função chama a 'function_itau_card_reader' via URL:
  environment_variables = {
    "TRANSACTIONS_FUNCTION_ITAU_CARD" = google_cloudfunctions_function.function_itau_card_reader.https_trigger_url
  }
}


# (B) function_itau_card_reader (Trigger HTTP)
data "archive_file" "function_itau_card_reader" {
  type        = "zip"
  source_dir  = "${path.module}/../function_itau_card_reader"
  output_path = "${path.module}/function_itau_card_reader.zip"
}

resource "google_storage_bucket_object" "function_itau_card_reader_zip" {
  name   = "function_itau_card_reader.zip"
  bucket = google_storage_bucket.functions_code_bucket.name
  source = data.archive_file.function_itau_card_reader.output_path
}

resource "google_cloudfunctions_function" "function_itau_card_reader" {
  name         = "function_itau_card_reader"
  description  = "Função que parseia o Excel (Itaú Card) e publica no Pub/Sub"
  runtime      = "python39"
  entry_point  = "parse_excel" 
  trigger_http = true
  project      = var.project_id
  region       = var.region

  source_archive_bucket = google_storage_bucket.functions_code_bucket.name
  source_archive_object = google_storage_bucket_object.function_itau_card_reader_zip.name

  # Passar por env var o tópico a ser usado
  environment_variables = {
    "PUBSUB_TOPIC" = google_pubsub_topic.personal_finance_flow.id
  }
}

#############################
# 4) PERMISSÕES (IAM)
#############################

# 4.1) Se function_file_arrival precisa ler objetos do data_bucket
resource "google_storage_bucket_iam_member" "data_bucket_viewer" {
  bucket = google_storage_bucket.data_bucket.name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_cloudfunctions_function.function_file_arrival.service_account_email}"
}

# 4.2) Se function_file_arrival ou function_itau_card_reader publica no tópico,
# conceder roles/pubsub.publisher ao service account de cada função

resource "google_pubsub_topic_iam_member" "publisher_file_arrival" {
  topic  = google_pubsub_topic.personal_finance_flow.name
  role   = "roles/pubsub.publisher"
  member = "serviceAccount:${google_cloudfunctions_function.function_file_arrival.service_account_email}"
}

resource "google_pubsub_topic_iam_member" "publisher_itau_reader" {
  topic  = google_pubsub_topic.personal_finance_flow.name
  role   = "roles/pubsub.publisher"
  member = "serviceAccount:${google_cloudfunctions_function.function_itau_card_reader.service_account_email}"
}

# 4.3) Se quiser invocar a function_itau_card_reader publicamente sem autenticação
resource "google_cloudfunctions_function_iam_member" "itau_reader_invoker" {
  project        = var.project_id
  region         = var.region
  cloud_function = google_cloudfunctions_function.function_itau_card_reader.name

  role   = "roles/cloudfunctions.invoker"
  member = "allUsers"
}

#############################
# 5) OUTPUTS (Opcional)
#############################

output "bucket_data" {
  value       = google_storage_bucket.data_bucket.name
  description = "Bucket que dispara a function_file_arrival"
}

output "itau_card_reader_url" {
  value       = google_cloudfunctions_function.function_itau_card_reader.https_trigger_url
  description = "URL da função itau_card_reader"
}

output "pubsub_topic" {
  value       = google_pubsub_topic.personal_finance_flow.name
  description = "Tópico Pub/Sub criado"
}

output "bq_table" {
  value       = google_bigquery_table.personal_finance_flow.id
  description = "Tabela BQ que recebe dados do Pub/Sub"
}
