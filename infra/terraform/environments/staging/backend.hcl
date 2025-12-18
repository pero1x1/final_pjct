bucket = "credit-scoring-tfstate-staging-b1gh235jp3f284fe2gdn"
key    = "staging/terraform.tfstate"
region = "ru-central1"

endpoints = {
  s3 = "https://storage.yandexcloud.net"
}

skip_region_validation      = true
skip_credentials_validation = true
skip_requesting_account_id  = true
skip_metadata_api_check     = true
use_path_style              = true
