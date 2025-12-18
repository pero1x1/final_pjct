module "storage" {
  source    = "../../modules/storage"
  project   = var.project
  env       = var.env
  folder_id = var.folder_id
}

module "network" {
  source      = "../../modules/network"
  project     = var.project
  env         = var.env
  zone        = var.zone
  subnet_cidr = "10.10.0.0/24"

  cluster_cidr = "10.96.0.0/16"
  service_cidr = "10.112.0.0/16"

  admin_cidrs = ["2.56.125.46/32", "205.237.111.90/32"]
  ssh_cidrs   = ["2.56.125.46/32", "205.237.111.90/32"]
}

module "kubernetes" {
  source      = "../../modules/kubernetes"
  k8s_version = "1.32"
  project     = var.project
  env         = var.env
  folder_id   = var.folder_id
  zone        = var.zone

  network_id = module.network.network_id
  subnet_id  = module.network.subnet_id

  master_security_group_ids = [
    module.network.sg_common_id,
    module.network.sg_master_id
  ]

  node_security_group_ids = [
    module.network.sg_common_id,
    module.network.sg_nodes_id,
    module.network.sg_nodeports_id,
    module.network.sg_ssh_id
  ]

  enable_gpu = false
}

module "monitoring" {
  source    = "../../modules/monitoring"
  project   = var.project
  env       = var.env
  folder_id = var.folder_id
}
