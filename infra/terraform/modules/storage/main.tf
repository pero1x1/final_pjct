resource "yandex_iam_service_account" "tfstate" {
  name        = "${var.project}-tfstate-${var.env}"
  description = "Service account for Terraform remote state bucket"
}

data "yandex_resourcemanager_folder" "current" {
  folder_id = var.folder_id
}

resource "yandex_resourcemanager_folder_iam_member" "tfstate_storage_admin" {
  folder_id = data.yandex_resourcemanager_folder.current.id
  role      = "storage.admin"
  member    = "serviceAccount:${yandex_iam_service_account.tfstate.id}"
}

resource "yandex_iam_service_account_static_access_key" "tfstate_key" {
  service_account_id = yandex_iam_service_account.tfstate.id
  description        = "Static access key for S3 backend"
}

resource "yandex_storage_bucket" "tfstate" {
  depends_on = [yandex_resourcemanager_folder_iam_member.tfstate_storage_admin]

  bucket    = "${var.project}-tfstate-${var.env}-${var.folder_id}"
  folder_id = var.folder_id

  # ВАЖНО: явно задаём S3-ключи
  access_key = yandex_iam_service_account_static_access_key.tfstate_key.access_key
  secret_key = yandex_iam_service_account_static_access_key.tfstate_key.secret_key

  versioning {
    enabled = true
  }

  anonymous_access_flags {
    read = false
    list = false
  }
}

