resource "yandex_vpc_network" "this" {
  name = "${var.project}-${var.env}-net"
}

resource "yandex_vpc_subnet" "this" {
  name           = "${var.project}-${var.env}-subnet-${var.zone}"
  zone           = var.zone
  network_id     = yandex_vpc_network.this.id
  v4_cidr_blocks = [var.subnet_cidr]
}

#  сервисный трафик
resource "yandex_vpc_security_group" "k8s_common" {
  name       = "${var.project}-${var.env}-k8s-common"
  network_id = yandex_vpc_network.this.id

  ingress {
    description       = "NLB health checks"
    protocol          = "TCP"
    from_port         = 0
    to_port           = 65535
    predefined_target = "loadbalancer_healthchecks"
  }

  ingress {
    description       = "Master <-> nodes service traffic (self)"
    protocol          = "ANY"
    from_port         = 0
    to_port           = 65535
    predefined_target = "self_security_group"
  }

  ingress {
    description    = "ICMP health checks from RFC1918"
    protocol       = "ICMP"
    v4_cidr_blocks = ["10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"]
  }

  egress {
    description       = "Master <-> nodes service traffic (self)"
    protocol          = "ANY"
    from_port         = 0
    to_port           = 65535
    predefined_target = "self_security_group"
  }
}

# трафик сервисов + исходящий в интернет для нод
resource "yandex_vpc_security_group" "k8s_nodes" {
  name       = "${var.project}-${var.env}-k8s-nodes"
  network_id = yandex_vpc_network.this.id

  ingress {
    description    = "Pods/Services traffic to nodes"
    protocol       = "ANY"
    from_port      = 0
    to_port        = 65535
    v4_cidr_blocks = [var.cluster_cidr, var.service_cidr]
  }

  egress {
    description    = "Nodes -> internet (pull images, updates, etc.)"
    protocol       = "ANY"
    from_port      = 0
    to_port        = 65535
    v4_cidr_blocks = ["0.0.0.0/0"]
  }
}

# доступ к Kubernetes API
resource "yandex_vpc_security_group" "k8s_master" {
  name       = "${var.project}-${var.env}-k8s-master"
  network_id = yandex_vpc_network.this.id

  ingress {
    description    = "K8s API 443"
    protocol       = "TCP"
    port           = 443
    v4_cidr_blocks = var.admin_cidrs
  }

  ingress {
    description    = "K8s API 6443"
    protocol       = "TCP"
    port           = 6443
    v4_cidr_blocks = var.admin_cidrs
  }

  egress {
    description    = "Master -> metric-server (4443) inside cluster"
    protocol       = "TCP"
    port           = 4443
    v4_cidr_blocks = [var.cluster_cidr]
  }

  egress {
    description    = "Master -> NTP"
    protocol       = "UDP"
    port           = 123
    v4_cidr_blocks = ["0.0.0.0/0"]
  }
}

# NodePort из интернета
resource "yandex_vpc_security_group" "k8s_nodeports" {
  name       = "${var.project}-${var.env}-k8s-nodeports"
  network_id = yandex_vpc_network.this.id

  ingress {
    description    = "NodePort range"
    protocol       = "TCP"
    from_port      = 30000
    to_port        = 32767
    v4_cidr_blocks = ["0.0.0.0/0"]
  }
}

# SSH к нодам
resource "yandex_vpc_security_group" "k8s_ssh" {
  name       = "${var.project}-${var.env}-k8s-ssh"
  network_id = yandex_vpc_network.this.id

  ingress {
    description    = "SSH to nodes"
    protocol       = "TCP"
    port           = 22
    v4_cidr_blocks = var.ssh_cidrs
  }
}


