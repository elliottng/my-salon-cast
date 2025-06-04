terraform {
  backend "gcs" {
    bucket  = "my-salon-cast-tf-state-1749009607"
    prefix  = "state"
  }
}
