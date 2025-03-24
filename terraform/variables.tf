variable "project_id" {
  type        = string
  description = "ID do projeto GCP"
}

variable "region" {
  type        = string
  description = "Região para as Cloud Functions."
  default     = "us-central1"
}

variable "location" {
  type        = string
  description = "Local (region) para o BigQuery. Pode ser 'US', 'EU', etc."
  default     = "US"
}
