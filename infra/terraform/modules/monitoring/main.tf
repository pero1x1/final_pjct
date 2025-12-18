resource "yandex_storage_bucket" "monitoring" {
  bucket    = "${var.project}-monitoring-${var.env}-${var.folder_id}"
  folder_id = var.folder_id

  versioning { enabled = true }

  anonymous_access_flags {
    read = false
    list = false
  }
}

