terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0" # Updated to a more recent version
    }
  }

}

provider "google" {
  project = var.project_id
  region  = var.region
  # zone    = var.zone # Zone is not always required at provider level
}

# We will add resource definitions here later, e.g., for Cloud Run, GCS buckets for app data, etc.
