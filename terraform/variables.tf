variable "project_id" {
  description = "The Google Cloud project ID"
  type        = string
}

variable "region" {
  description = "The Google Cloud region"
  type        = string
  default     = "us-central1"
}

variable "zone" {
  description = "The Google Cloud zone"
  type        = string
  default     = "us-central1-a"
}

variable "gcs_bucket_tf_state" {
  description = "The GCS bucket for Terraform state"
  type        = string
  default     = "my-salon-cast-tf-state"
}
