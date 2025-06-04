output "staging_service_url" {
  description = "URL of the staging MCP server"
  value       = google_cloud_run_v2_service.mcp_server_staging.uri
}

output "production_service_url" {
  description = "URL of the production MCP server"
  value       = google_cloud_run_v2_service.mcp_server_production.uri
}

output "staging_audio_bucket" {
  description = "Name of the staging audio storage bucket"
  value       = google_storage_bucket.staging_audio.name
}

output "production_audio_bucket" {
  description = "Name of the production audio storage bucket"
  value       = google_storage_bucket.production_audio.name
}

output "staging_database_bucket" {
  description = "Name of the staging database storage bucket"
  value       = google_storage_bucket.staging_database.name
}

output "production_database_bucket" {
  description = "Name of the production database storage bucket"
  value       = google_storage_bucket.production_database.name
}

output "service_account_email" {
  description = "Email of the service account used by the MCP server"
  value       = google_service_account.mcp_server.email
}
