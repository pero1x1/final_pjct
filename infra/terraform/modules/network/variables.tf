variable "project" { type = string }
variable "env" { type = string }

variable "zone" { type = string }
variable "subnet_cidr" { type = string }

variable "cluster_cidr" { type = string }
variable "service_cidr" { type = string }

variable "admin_cidrs" { type = list(string) }
variable "ssh_cidrs"   { type = list(string) }
