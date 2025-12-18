# CPU node group
variable "cpu_nodes" {
  type    = number
  default = 2
}

variable "cpu_cores" {
  type    = number
  default = 4
}

variable "cpu_memory" {
  type    = number
  default = 8
}

variable "cpu_disk_gb" {
  type    = number
  default = 64
}

# GPU node group
variable "enable_gpu" {
  type    = bool
  default = false
}

variable "gpu_nodes" {
  type    = number
  default = 1
}

variable "gpu_cores" {
  type    = number
  default = 8
}

variable "gpu_memory" {
  type    = number
  default = 64
}

variable "gpu_count" {
  type    = number
  default = 1
}

variable "gpu_disk_gb" {
  type    = number
  default = 100
}

variable "project" {
  type = string
}

variable "env" {
  type = string
}

variable "folder_id" {
  type = string
}

variable "zone" {
  type = string
}

variable "network_id" {
  type = string
}

variable "subnet_id" {
  type = string
}

variable "master_security_group_ids" {
  type = list(string)
}

variable "node_security_group_ids" {
  type = list(string)
}

variable "k8s_version" {
  type    = string
  default = "1.32"
}

variable "gpu_platform_id" {
  type    = string
  default = "gpu-standard-v3"
}
