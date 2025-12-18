output "network_id" { value = yandex_vpc_network.this.id }
output "subnet_id"  { value = yandex_vpc_subnet.this.id }

output "sg_common_id"    { value = yandex_vpc_security_group.k8s_common.id }
output "sg_nodes_id"     { value = yandex_vpc_security_group.k8s_nodes.id }
output "sg_master_id"    { value = yandex_vpc_security_group.k8s_master.id }
output "sg_nodeports_id" { value = yandex_vpc_security_group.k8s_nodeports.id }
output "sg_ssh_id"       { value = yandex_vpc_security_group.k8s_ssh.id }
