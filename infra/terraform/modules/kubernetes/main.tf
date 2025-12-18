resource "yandex_iam_service_account" "k8s" {
  name        = "${var.project}-k8s-${var.env}"
  description = "SA for Managed Kubernetes cluster"
}

resource "yandex_iam_service_account" "k8s_nodes" {
  name        = "${var.project}-k8s-nodes-${var.env}"
  description = "SA for Managed Kubernetes node groups"
}

# не ловить “PermissionDenied” на каждом шаге
resource "yandex_resourcemanager_folder_iam_member" "k8s_editor" {
  folder_id = var.folder_id
  role      = "editor"
  member    = "serviceAccount:${yandex_iam_service_account.k8s.id}"
}

resource "yandex_resourcemanager_folder_iam_member" "k8s_nodes_editor" {
  folder_id = var.folder_id
  role      = "editor"
  member    = "serviceAccount:${yandex_iam_service_account.k8s_nodes.id}"
}

resource "yandex_kubernetes_cluster" "this" {
  name       = "${var.project}-${var.env}"
  network_id = var.network_id

  master {
    version = var.k8s_version

    zonal {
      zone      = var.zone
      subnet_id = var.subnet_id
    }

    public_ip          = true
    security_group_ids = var.master_security_group_ids
  }

  service_account_id      = yandex_iam_service_account.k8s.id
  node_service_account_id = yandex_iam_service_account.k8s_nodes.id

  # сетевые политики 
  network_implementation {
    cilium {}
  }

  depends_on = [
    yandex_resourcemanager_folder_iam_member.k8s_editor,
    yandex_resourcemanager_folder_iam_member.k8s_nodes_editor
  ]
}

resource "yandex_kubernetes_node_group" "cpu" {
  cluster_id = yandex_kubernetes_cluster.this.id
  name       = "${var.project}-${var.env}-cpu"

  instance_template {
    platform_id = "standard-v3"

    resources {
      cores  = var.cpu_cores
      memory = var.cpu_memory
    }

    boot_disk {
      type = "network-ssd"
      size = var.cpu_disk_gb
    }

    network_interface {
      subnet_ids         = [var.subnet_id]
      nat                = true
      security_group_ids = var.node_security_group_ids
    }
  }

  scale_policy {
    fixed_scale {
      size = var.cpu_nodes
    }
  }

  allocation_policy {
    location { zone = var.zone }
  }
}

resource "yandex_kubernetes_node_group" "gpu" {
  count     = var.enable_gpu ? 1 : 0
  cluster_id = yandex_kubernetes_cluster.this.id
  name       = "${var.project}-${var.env}-gpu"

  instance_template {
    platform_id = var.gpu_platform_id

    resources {
      cores  = var.gpu_cores
      memory = var.gpu_memory
      gpus   = var.gpu_count
    }

    boot_disk {
      type = "network-ssd"
      size = var.gpu_disk_gb
    }

    network_interface {
      subnet_ids         = [var.subnet_id]
      nat                = true
      security_group_ids = var.node_security_group_ids
    }
  }

  scale_policy {
    fixed_scale {
      size = var.gpu_nodes
    }
  }

  allocation_policy {
    location { zone = var.zone }
  }
}

