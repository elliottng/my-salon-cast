variable "project_id" {
  description = "The Google Cloud project ID"
  type        = string
}

variable "region" {
  description = "The Google Cloud region"
  type        = string
  default     = "us-west1"
}

variable "zone" {
  description = "The Google Cloud zone"
  type        = string
  default     = "us-west1-a"
}

variable "gcs_bucket_tf_state" {
  description = "The GCS bucket for Terraform state"
  type        = string
  default     = "my-salon-cast-tf-state"
}

variable "environment" {
  description = "Deployment environment (staging or production)"
  type        = string
  default     = "staging"
  validation {
    condition     = contains(["staging", "production"], var.environment)
    error_message = "Environment must be either 'staging' or 'production'."
  }
}

variable "gemini_api_key" {
  description = "Gemini API key for podcast generation"
  type        = string
  sensitive   = true
}
