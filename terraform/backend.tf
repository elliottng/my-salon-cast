terraform {
  backend "gcs" {
    bucket  = "my-salon-cast-tf-state"
    prefix  = "state"
  }
}
