output "tfstate_bucket" {
  value = module.storage.bucket_name
}

output "tfstate_access_key" {
  value     = module.storage.access_key
  sensitive = true
}

output "tfstate_secret_key" {
  value     = module.storage.secret_key
  sensitive = true
}