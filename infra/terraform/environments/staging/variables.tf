variable "cloud_id" {
  type = string
}

variable "folder_id" {
  type = string
}

variable "zone" {
  type    = string
  default = "ru-central1-a"
}

variable "sa_key_file" {
  type        = string
  description = "Path to service account key json"
}

variable "project" {
  type    = string
  default = "credit-scoring"
}

variable "env" {
  type    = string
  default = "staging"
}

