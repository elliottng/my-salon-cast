terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# Enable required APIs
resource "google_project_service" "apis" {
  for_each = toset([
    "run.googleapis.com",
    "cloudbuild.googleapis.com",
    "storage-api.googleapis.com",
    "storage-component.googleapis.com"
  ])
  
  project = var.project_id
  service = each.value
}

# Cloud Storage buckets for staging environment
resource "google_storage_bucket" "staging_audio" {
  name          = "${var.project_id}-staging-audio"
  location      = var.region
  force_destroy = true

  uniform_bucket_level_access = true

  lifecycle_rule {
    condition {
      age = 30
    }
    action {
      type = "Delete"
    }
  }
}

resource "google_storage_bucket" "staging_database" {
  name          = "${var.project_id}-staging-database"
  location      = var.region
  force_destroy = true

  uniform_bucket_level_access = true

  versioning {
    enabled = true
  }

  lifecycle_rule {
    condition {
      num_newer_versions = 5
    }
    action {
      type = "Delete"
    }
  }
}

# Cloud Storage buckets for production environment
resource "google_storage_bucket" "production_audio" {
  name          = "${var.project_id}-production-audio"
  location      = var.region
  force_destroy = false

  uniform_bucket_level_access = true

  lifecycle_rule {
    condition {
      age = 90
    }
    action {
      type = "Delete"
    }
  }
}

resource "google_storage_bucket" "production_database" {
  name          = "${var.project_id}-production-database"
  location      = var.region
  force_destroy = false

  uniform_bucket_level_access = true

  versioning {
    enabled = true
  }

  lifecycle_rule {
    condition {
      num_newer_versions = 10
    }
    action {
      type = "Delete"
    }
  }
}

# Service account for Cloud Run services
resource "google_service_account" "mcp_server" {
  account_id   = "mcp-server"
  display_name = "MCP Server Service Account"
  description  = "Service account for MySalonCast MCP server"
}

# IAM bindings for service account
resource "google_project_iam_member" "mcp_server_storage" {
  project = var.project_id
  role    = "roles/storage.objectAdmin"
  member  = "serviceAccount:${google_service_account.mcp_server.email}"
}

# Cloud Run service for staging
resource "google_cloud_run_v2_service" "mcp_server_staging" {
  name     = "mcp-server-staging"
  location = var.region

  template {
    service_account = google_service_account.mcp_server.email
    
    scaling {
      min_instance_count = 0
      max_instance_count = 1
    }

    containers {
      image = "gcr.io/${var.project_id}/mcp-server:latest"
      
      resources {
        limits = {
          cpu    = "1000m"
          memory = "512Mi"
        }
      }

      env {
        name  = "ENVIRONMENT"
        value = "staging"
      }

      env {
        name  = "PROJECT_ID"
        value = var.project_id
      }

      env {
        name  = "REGION"
        value = var.region
      }

      env {
        name  = "AUDIO_BUCKET"
        value = google_storage_bucket.staging_audio.name
      }

      env {
        name  = "DATABASE_BUCKET"
        value = google_storage_bucket.staging_database.name
      }

      env {
        name  = "GEMINI_API_KEY"
        value = var.gemini_api_key
      }

      env {
        name  = "ALLOWED_ORIGINS"
        value = "https://claude.ai,https://inspect.mcp.garden"
      }

      ports {
        container_port = 8000
      }
    }
  }

  depends_on = [google_project_service.apis]
}

# Cloud Run service for production
resource "google_cloud_run_v2_service" "mcp_server_production" {
  name     = "mcp-server-production"
  location = var.region

  template {
    service_account = google_service_account.mcp_server.email
    
    scaling {
      min_instance_count = 0
      max_instance_count = 4
    }

    containers {
      image = "gcr.io/${var.project_id}/mcp-server:latest"
      
      resources {
        limits = {
          cpu    = "2000m"
          memory = "1Gi"
        }
      }

      env {
        name  = "ENVIRONMENT"
        value = "production"
      }

      env {
        name  = "PROJECT_ID"
        value = var.project_id
      }

      env {
        name  = "REGION"
        value = var.region
      }

      env {
        name  = "AUDIO_BUCKET"
        value = google_storage_bucket.production_audio.name
      }

      env {
        name  = "DATABASE_BUCKET"
        value = google_storage_bucket.production_database.name
      }

      env {
        name  = "GEMINI_API_KEY"
        value = var.gemini_api_key
      }

      env {
        name  = "ALLOWED_ORIGINS"
        value = "https://claude.ai,https://inspect.mcp.garden"
      }

      ports {
        container_port = 8000
      }
    }
  }

  depends_on = [google_project_service.apis]
}

# IAM policy for public access to staging (for testing)
resource "google_cloud_run_service_iam_member" "staging_public" {
  location = google_cloud_run_v2_service.mcp_server_staging.location
  service  = google_cloud_run_v2_service.mcp_server_staging.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# IAM policy for authenticated access to production
resource "google_cloud_run_service_iam_member" "production_auth" {
  location = google_cloud_run_v2_service.mcp_server_production.location
  service  = google_cloud_run_v2_service.mcp_server_production.name
  role     = "roles/run.invoker"
  member   = "allAuthenticatedUsers"
}
