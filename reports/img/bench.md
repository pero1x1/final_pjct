# Этап 1 Benchmark и качество (NN → ONNX → INT8)

## 1) Качество
Torch AUC: 0.76781  
ONNX  AUC: 0.76781  
INT8  AUC: 0.76533  
Drop INT8 vs ONNX: 0.00248
Квантизация почти не ухудшила качество.

## 2) Скорость
CPU лучший кейс
Torch (threads=4): 0.183 ms/batch
ONNX FP32: 6.974 ms/batch
ONNX INT8: 7.386 ms/batch

## 3) Итог
Модель малой сложности CPU достаточно
Выбор GPU экономически нецелесообразен 

ONNX и INT8 прошли валидацию и почти не ухудшили качество. 
На CPU PyTorch быстрее ONNX из-за вызова inference из Python и очень малого размера модели.
Для продакшена выбираем CPU, а GPU не требуется. 

models/model.onnx: 2.5 KB
models/model.int8.onnx: 17.1 KB
models/nn_model.pt: 50.6 KB  

# Этап 2 

## Terraform конфигурация валидна 
(.venv) PS C:\Users\USER\Desktop\credits-main\infra\terraform\environments\staging> terraform validate
Success! The configuration is valid.

## Модульная структура (VPC / K8s / Storage / Monitoring) реально в state
(.venv) PS C:\Users\USER\Desktop\credits-main\infra\terraform\environments\staging> terraform state list
module.kubernetes.yandex_iam_service_account.k8s
module.kubernetes.yandex_iam_service_account.k8s_nodes
module.kubernetes.yandex_kubernetes_cluster.this
module.kubernetes.yandex_kubernetes_node_group.cpu
module.kubernetes.yandex_resourcemanager_folder_iam_member.k8s_editor
module.kubernetes.yandex_resourcemanager_folder_iam_member.k8s_nodes_editor
module.monitoring.yandex_storage_bucket.monitoring
module.network.yandex_vpc_network.this
module.network.yandex_vpc_security_group.k8s_common
module.network.yandex_vpc_security_group.k8s_master
module.network.yandex_vpc_security_group.k8s_nodeports
module.network.yandex_vpc_security_group.k8s_nodes
module.network.yandex_vpc_security_group.k8s_ssh
module.network.yandex_vpc_subnet.this
module.storage.data.yandex_resourcemanager_folder.current
module.storage.yandex_iam_service_account.tfstate
module.storage.yandex_iam_service_account_static_access_key.tfstate_key
module.storage.yandex_resourcemanager_folder_iam_member.tfstate_storage_admin
module.storage.yandex_storage_bucket.tfstate

## Remote state настроен в Object Storage
(.venv) PS C:\Users\USER\Desktop\credits-main\infra\terraform\environments\staging> yc storage bucket list
+--------------------------------------------------------+----------------------+----------+-----------------------+---------------------+
|                          NAME                          |      FOLDER ID       | MAX SIZE | DEFAULT STORAGE CLASS |     CREATED AT      |     
+--------------------------------------------------------+----------------------+----------+-----------------------+---------------------+     
| credit-scoring-tfstate-staging-b1gh235jp3f284fe2gdn    | b1gh235jp3f284fe2gdn |        0 | STANDARD              | 2025-12-14 14:03:12 |     
| credit-scoring-monitoring-staging-b1gh235jp3f284fe2gdn | b1gh235jp3f284fe2gdn |        0 | STANDARD              | 2025-12-15 12:13:37 |     
+--------------------------------------------------------+----------------------+----------+-----------------------+---------------------+     

(.venv) PS C:\Users\USER\Desktop\credits-main\infra\terraform\environments\staging> $bucket="credit-scoring-tfstate-staging-b1gh235jp3f284fe2gdn"
(.venv) PS C:\Users\USER\Desktop\credits-main\infra\terraform\environments\staging> yc storage s3api list-objects --bucket $bucket
contents:
  - key: staging/terraform.tfstate
    last_modified: "2025-12-15T12:48:19.974Z"
    etag: '"873d0637b5e3f53462c8a6aaa25d7b06"'
    size: "35304"
    owner:
      id: ajeu27bvsvb5a6r4vimd
      display_name: ajeu27bvsvb5a6r4vimd
    storage_class: STANDARD
name: credit-scoring-tfstate-staging-b1gh235jp3f284fe2gdn
max_keys: "1000"
key_count: "1"
request_id: b95f403b995cad73

## VPC создана (network + subnet)
(.venv) PS C:\Users\USER\Desktop\credits-main\infra\terraform\environments\staging> yc vpc network list --folder-id b1gh235jp3f284fe2gdn
+----------------------+----------------------------+
|          ID          |            NAME            |
+----------------------+----------------------------+
| enpcaogh9dhkplelr2d4 | credit-scoring-staging-net |
| enpr46jiksjvj4mskn9o | default                    |
+----------------------+----------------------------+

(.venv) PS C:\Users\USER\Desktop\credits-main\infra\terraform\environments\staging> yc vpc subnet list  --folder-id b1gh235jp3f284fe2gdn
+----------------------+---------------------------------------------+----------------------+----------------+---------------+-----------------+
|          ID          |                    NAME                     |      NETWORK ID      | ROUTE TABLE ID |     ZONE      |      RANGE      |
+----------------------+---------------------------------------------+----------------------+----------------+---------------+-----------------+
| e2lk5hlhq9m8d97ser5c | default-ru-central1-b                       | enpr46jiksjvj4mskn9o |                | ru-central1-b | [10.129.0.0/24] |
| e9b5q0rgvbqk69nlp1vq | default-ru-central1-a                       | enpr46jiksjvj4mskn9o |                | ru-central1-a | [10.128.0.0/24] |
| fl8bbukicmtkceo6t5d1 | credit-scoring-staging-subnet-ru-central1-d | enpcaogh9dhkplelr2d4 |                | ru-central1-d | [10.10.0.0/24]  |
| fl8gj3j272ag1merj9l4 | default-ru-central1-d                       | enpr46jiksjvj4mskn9o |                | ru-central1-d | [10.130.0.0/24] |
+----------------------+---------------------------------------------+----------------------+----------------+---------------+-----------------+

## Security Groups и сетевые правила (network policy / SG)
(.venv) PS C:\Users\USER\Desktop\credits-main\infra\terraform\environments\staging> yc vpc security-group list --folder-id b1gh235jp3f284fe2gdn

+----------------------+--------------------------------------+--------------------------------+----------------------+
|          ID          |                 NAME                 |          DESCRIPTION           |      NETWORK-ID      |
+----------------------+--------------------------------------+--------------------------------+----------------------+
| enp3dgbohisa2prjkv11 | credit-scoring-staging-k8s-master    |                                | enpcaogh9dhkplelr2d4 |
| enp8pahn31sm4jgo6p9q | credit-scoring-staging-k8s-nodes     |                                | enpcaogh9dhkplelr2d4 |
| enpiujuflu9q77i9juea | credit-scoring-staging-k8s-ssh       |                                | enpcaogh9dhkplelr2d4 |
| enpl9ohrr031jg49lhae | credit-scoring-staging-k8s-nodeports |                                | enpcaogh9dhkplelr2d4 |
| enpp9ug39804fn1it44t | default-sg-enpcaogh9dhkplelr2d4      | Default security group for     | enpcaogh9dhkplelr2d4 |
|                      |                                      | network                        |                      |
| enpsokbimuv8mecvc655 | default-sg-enpr46jiksjvj4mskn9o      | Default security group for     | enpr46jiksjvj4mskn9o |
|                      |                                      | network                        |                      |
| enpveou5no9ghf7t1pc7 | credit-scoring-staging-k8s-common    |                                | enpcaogh9dhkplelr2d4 |
+----------------------+--------------------------------------+--------------------------------+----------------------+

(.venv) PS C:\Users\USER\Desktop\credits-main\infra\terraform\environments\staging> 
(.venv) PS C:\Users\USER\Desktop\credits-main\infra\terraform\environments\staging> terraform state show module.network.yandex_vpc_security_group.k8s_master
# module.network.yandex_vpc_security_group.k8s_master:
resource "yandex_vpc_security_group" "k8s_master" {
    created_at  = "2025-12-15T12:13:46Z"
    description = null
    folder_id   = "b1gh235jp3f284fe2gdn"
    id          = "enp3dgbohisa2prjkv11"
    labels      = {}
    name        = "credit-scoring-staging-k8s-master"
    network_id  = "enpcaogh9dhkplelr2d4"
    status      = "ACTIVE"

    egress {
        description       = "Master -> NTP"
        from_port         = -1
        id                = "enprimd3bpu66nck7fep"
        labels            = {}
        port              = 123
        predefined_target = null
        protocol          = "UDP"
        security_group_id = null
        to_port           = -1
        v4_cidr_blocks    = [
            "0.0.0.0/0",
        ]
        v6_cidr_blocks    = []
    }
    egress {
        description       = "Master -> metric-server (4443) inside cluster"
        from_port         = -1
        id                = "enpkkpt4aqa78lr11n4d"
        labels            = {}
        port              = 4443
        predefined_target = null
        protocol          = "TCP"
        security_group_id = null
        to_port           = -1
        v4_cidr_blocks    = [
            "10.96.0.0/16",
        ]
        v6_cidr_blocks    = []
    }

    ingress {
        description       = "K8s API 443"
        from_port         = -1
        id                = "enpvu84mk077kc4i14k1"
        labels            = {}
        port              = 443
        predefined_target = null
        protocol          = "TCP"
        security_group_id = null
        to_port           = -1
        v4_cidr_blocks    = [
            "2.56.125.46/32",
        ]
        v6_cidr_blocks    = []
    }
    ingress {
        description       = "K8s API 6443"
        from_port         = -1
        id                = "enpn1tqvf0tldqur1k6i"
        labels            = {}
        port              = 6443
        predefined_target = null
        protocol          = "TCP"
        security_group_id = null
        to_port           = -1
        v4_cidr_blocks    = [
            "2.56.125.46/32",
        ]
        v6_cidr_blocks    = []
    }
}
(.venv) PS C:\Users\USER\Desktop\credits-main\infra\terraform\environments\staging> terraform state show module.network.yandex_vpc_security_group.k8s_nodes
# module.network.yandex_vpc_security_group.k8s_nodes:
resource "yandex_vpc_security_group" "k8s_nodes" {
    created_at  = "2025-12-15T12:13:43Z"
    description = null
    folder_id   = "b1gh235jp3f284fe2gdn"
    id          = "enp8pahn31sm4jgo6p9q"
    labels      = {}
    name        = "credit-scoring-staging-k8s-nodes"
    network_id  = "enpcaogh9dhkplelr2d4"
    status      = "ACTIVE"

    egress {
        description       = "Nodes -> internet (pull images, updates, etc.)"
        from_port         = 0
        id                = "enpcto6ashe49db1v5r1"
        labels            = {}
        port              = -1
        predefined_target = null
        protocol          = "ANY"
        security_group_id = null
        to_port           = 65535
        v4_cidr_blocks    = [
            "0.0.0.0/0",
        ]
        v6_cidr_blocks    = []
    }

    ingress {
        description       = "Pods/Services traffic to nodes"
        from_port         = 0
        id                = "enp9jtd18b4f781r973d"
        labels            = {}
        port              = -1
        predefined_target = null
        protocol          = "ANY"
        security_group_id = null
        to_port           = 65535
        from_port         = 0
        id                = "enp9jtd18b4f781r973d"
        labels            = {}
        port              = -1
        predefined_target = null
        protocol          = "ANY"
        security_group_id = null
        to_port           = 65535
        v4_cidr_blocks    = [
        id                = "enp9jtd18b4f781r973d"
        labels            = {}
        port              = -1
        predefined_target = null
        protocol          = "ANY"
        security_group_id = null
        to_port           = 65535
        v4_cidr_blocks    = [
        labels            = {}
        port              = -1
        predefined_target = null
        protocol          = "ANY"
        security_group_id = null
        to_port           = 65535
        v4_cidr_blocks    = [
            "10.96.0.0/16",
            "10.112.0.0/16",
        port              = -1
        predefined_target = null
        protocol          = "ANY"
        security_group_id = null
        to_port           = 65535
        v4_cidr_blocks    = [
            "10.96.0.0/16",
            "10.112.0.0/16",
        predefined_target = null
        protocol          = "ANY"
        security_group_id = null
        to_port           = 65535
        v4_cidr_blocks    = [
            "10.96.0.0/16",
            "10.112.0.0/16",
        security_group_id = null
        to_port           = 65535
        v4_cidr_blocks    = [
            "10.96.0.0/16",
            "10.112.0.0/16",
        ]
        v6_cidr_blocks    = []
        v4_cidr_blocks    = [
            "10.96.0.0/16",
            "10.112.0.0/16",
        ]
        v6_cidr_blocks    = []
            "10.96.0.0/16",
            "10.112.0.0/16",
        ]
        v6_cidr_blocks    = []
    }
        ]
        v6_cidr_blocks    = []
    }
    }

## Managed Kubernetes создан и работает
(.venv) PS C:\Users\USER\Desktop\credits-main\infra\terraform\environments\staging> yc managed-kubernetes cluster list
+----------------------+------------------------+---------------------+---------+---------+------------------------+--------------------+      
+----------------------+------------------------+---------------------+---------+---------+------------------------+--------------------+      
|          ID          |          NAME          |     CREATED AT      | HEALTH  | STATUS  |   EXTERNAL ENDPOINT    | INTERNAL ENDPOINT  |      
+----------------------+------------------------+---------------------+---------+---------+------------------------+--------------------+      
| catnksjlj5ms8glck9pr | credit-scoring-staging | 2025-12-15 12:38:36 | HEALTHY | RUNNING | https://158.160.214.99 | https://10.10.0.28 |      
+----------------------+------------------------+---------------------+---------+---------+------------------------+--------------------+      

(.venv) PS C:\Users\USER\Desktop\credits-main\infra\terraform\environments\staging> yc managed-kubernetes cluster list-node-groups --id catnksjlj5ms8glck9pr
+----------------------+----------------------------+----------------------+---------------------+---------+------+
|          ID          |            NAME            |  INSTANCE GROUP ID   |     CREATED AT      | STATUS  | SIZE |
+----------------------+----------------------------+----------------------+---------------------+---------+------+
| catgc305288p0b0ku078 | credit-scoring-staging-cpu | cl1qlcqt0anrnjsmic9v | 2025-12-15 12:45:53 | RUNNING |    2 |
+----------------------+----------------------------+----------------------+---------------------+---------+------+

## Доступ к кластеру через kubectl, ноды Ready 
(.venv) PS C:\Users\USER\Desktop\credits-main\infra\terraform\environments\staging> yc managed-kubernetes cluster get-credentials --id catnksjlj5ms8glck9pr --external --force

Context 'yc-credit-scoring-staging' was added as default to kubeconfig 'C:\Users\USER\.kube\config'.
Check connection to cluster using 'kubectl cluster-info --kubeconfig C:\Users\USER\.kube\config'.

Note, that authentication depends on 'yc' and its config profile 'default'.
To access clusters using the Kubernetes API, please use Kubernetes Service Account.
(.venv) PS C:\Users\USER\Desktop\credits-main\infra\terraform\environments\staging> kubectl cluster-info
Kubernetes control plane is running at https://158.160.214.99
CoreDNS is running at https://158.160.214.99/api/v1/namespaces/kube-system/services/kube-dns:dns/proxy

To further debug and diagnose cluster problems, use 'kubectl cluster-info dump'.
(.venv) PS C:\Users\USER\Desktop\credits-main\infra\terraform\environments\staging> kubectl get nodes -o wide
NAME                        STATUS   ROLES    AGE   VERSION   INTERNAL-IP   EXTERNAL-IP       OS-IMAGE             KERNEL-VERSION       CONTAINER-RUNTIME
cl1qlcqt0anrnjsmic9v-ekof   Ready    <none>   15h   v1.32.1   10.10.0.8     158.160.217.188   Ubuntu 22.04.5 LTS   5.15.0-161-generic   containerd://1.7.27
cl1qlcqt0anrnjsmic9v-owix   Ready    <none>   15h   v1.32.1   10.10.0.19    158.160.214.60    Ubuntu 22.04.5 LTS   5.15.0-161-generic   containerd://1.7.27
(.venv) PS C:\Users\USER\Desktop\credits-main\infra\terraform\environments\staging> kubectl get pods -A
NAMESPACE     NAME                                 READY   STATUS      RESTARTS   AGE
kube-system   cilium-jqbwb                         1/1     Running     0          15h
kube-system   cilium-operator-6bbd58d766-x8kgq     1/1     Running     0          15h
kube-system   cilium-vc2q9                         1/1     Running     0          15h
kube-system   coredns-768847b69f-hsv7q             1/1     Running     0          15h
kube-system   coredns-768847b69f-rxlzr             1/1     Running     0          15h
kube-system   hubble-generate-certs-928nm          0/1     Completed   0          18m
(.venv) PS C:\Users\USER\Desktop\credits-main\infra\terraform\environments\staging> kubectl get nodes -o wide
NAME                        STATUS   ROLES    AGE   VERSION   INTERNAL-IP   EXTERNAL-IP       OS-IMAGE             KERNEL-VERSION       CONTAINER-RUNTIME
cl1qlcqt0anrnjsmic9v-ekof   Ready    <none>   15h   v1.32.1   10.10.0.8     158.160.217.188   Ubuntu 22.04.5 LTS   5.15.0-161-generic   containerd://1.7.27
cl1qlcqt0anrnjsmic9v-owix   Ready    <none>   15h   v1.32.1   10.10.0.19    158.160.214.60    Ubuntu 22.04.5 LTS   5.15.0-161-generic   containerd://1.7.27
(.venv) PS C:\Users\USER\Desktop\credits-main\infra\terraform\environments\staging> kubectl get pods -A
NAMESPACE     NAME                                 READY   STATUS      RESTARTS   AGE
kube-system   cilium-jqbwb                         1/1     Running     0          15h
kube-system   cilium-operator-6bbd58d766-x8kgq     1/1     Running     0          15h
kube-system   cilium-vc2q9                         1/1     Running     0          15h
kube-system   coredns-768847b69f-hsv7q             1/1     Running     0          15h
kube-system   coredns-768847b69f-rxlzr             1/1     Running     0          15h
kube-system   hubble-generate-certs-928nm          0/1     Completed   0          18m
kube-system   hubble-relay-6cf7b87694-k6lll        1/1     Running     0          15h
kube-system   ip-masq-agent-j5bnb                  1/1     Running     0          15h
kube-system   ip-masq-agent-jxzgr                  1/1     Running     0          15h
kube-system   kube-dns-autoscaler-66b55897-c5vjn   1/1     Running     0          15h
kube-system   metrics-server-8689cb9795-msq67      1/1     Running     0          15h
kube-system   metrics-server-8689cb9795-nrtd2      1/1     Running     0          15h
ER-RUNTIME
cl1qlcqt0anrnjsmic9v-ekof   Ready    <none>   15h   v1.32.1   10.10.0.8     158.160.217.188   Ubuntu 22.04.5 LTS   5.15.0-161-generic   containerd://1.7.27
cl1qlcqt0anrnjsmic9v-owix   Ready    <none>   15h   v1.32.1   10.10.0.19    158.160.214.60    Ubuntu 22.04.5 LTS   5.15.0-161-generic   containerd://1.7.27
(.venv) PS C:\Users\USER\Desktop\credits-main\infra\terraform\environments\staging> kubectl get pods -A
NAMESPACE     NAME                                 READY   STATUS      RESTARTS   AGE
kube-system   cilium-jqbwb                         1/1     Running     0          15h
kube-system   cilium-operator-6bbd58d766-x8kgq     1/1     Running     0          15h
kube-system   cilium-vc2q9                         1/1     Running     0          15h
kube-system   coredns-768847b69f-hsv7q             1/1     Running     0          15h
kube-system   coredns-768847b69f-rxlzr             1/1     Running     0          15h
kube-system   hubble-generate-certs-928nm          0/1     Completed   0          18m
kube-system   hubble-relay-6cf7b87694-k6lll        1/1     Running     0          15h
kube-system   ip-masq-agent-j5bnb                  1/1     Running     0          15h
kube-system   ip-masq-agent-jxzgr                  1/1     Running     0          15h
kube-system   kube-dns-autoscaler-66b55897-c5vjn   1/1     Running     0          15h
kube-system   metrics-server-8689cb9795-msq67      1/1     Running     0          15h
kube-system   metrics-server-8689cb9795-nrtd2      1/1     Running     0          15h
kube-system   npd-v0.8.0-fr7c4                     1/1     Running     0          15h
kube-system   npd-v0.8.0-kw7hd                     1/1     Running     0          15h
kube-system   yc-disk-csi-node-v2-ck7dw            6/6     Running     0          15h
cl1qlcqt0anrnjsmic9v-owix   Ready    <none>   15h   v1.32.1   10.10.0.19    158.160.214.60    Ubuntu 22.04.5 LTS   5.15.0-161-generic   containerd://1.7.27
(.venv) PS C:\Users\USER\Desktop\credits-main\infra\terraform\environments\staging> kubectl get pods -A
NAMESPACE     NAME                                 READY   STATUS      RESTARTS   AGE
kube-system   cilium-jqbwb                         1/1     Running     0          15h
kube-system   cilium-operator-6bbd58d766-x8kgq     1/1     Running     0          15h
kube-system   cilium-vc2q9                         1/1     Running     0          15h
kube-system   coredns-768847b69f-hsv7q             1/1     Running     0          15h
kube-system   coredns-768847b69f-rxlzr             1/1     Running     0          15h
kube-system   hubble-generate-certs-928nm          0/1     Completed   0          18m
kube-system   hubble-relay-6cf7b87694-k6lll        1/1     Running     0          15h
kube-system   ip-masq-agent-j5bnb                  1/1     Running     0          15h
kube-system   ip-masq-agent-jxzgr                  1/1     Running     0          15h
kube-system   kube-dns-autoscaler-66b55897-c5vjn   1/1     Running     0          15h
kube-system   metrics-server-8689cb9795-msq67      1/1     Running     0          15h
kube-system   metrics-server-8689cb9795-nrtd2      1/1     Running     0          15h
kube-system   npd-v0.8.0-fr7c4                     1/1     Running     0          15h
kube-system   npd-v0.8.0-kw7hd                     1/1     Running     0          15h
kube-system   yc-disk-csi-node-v2-ck7dw            6/6     Running     0          15h
NAMESPACE     NAME                                 READY   STATUS      RESTARTS   AGE
kube-system   cilium-jqbwb                         1/1     Running     0          15h
kube-system   cilium-operator-6bbd58d766-x8kgq     1/1     Running     0          15h
kube-system   cilium-vc2q9                         1/1     Running     0          15h
kube-system   coredns-768847b69f-hsv7q             1/1     Running     0          15h
kube-system   coredns-768847b69f-rxlzr             1/1     Running     0          15h
kube-system   hubble-generate-certs-928nm          0/1     Completed   0          18m
kube-system   hubble-relay-6cf7b87694-k6lll        1/1     Running     0          15h
kube-system   ip-masq-agent-j5bnb                  1/1     Running     0          15h
kube-system   ip-masq-agent-jxzgr                  1/1     Running     0          15h
kube-system   kube-dns-autoscaler-66b55897-c5vjn   1/1     Running     0          15h
kube-system   metrics-server-8689cb9795-msq67      1/1     Running     0          15h
kube-system   metrics-server-8689cb9795-nrtd2      1/1     Running     0          15h
kube-system   npd-v0.8.0-fr7c4                     1/1     Running     0          15h
kube-system   npd-v0.8.0-kw7hd                     1/1     Running     0          15h
kube-system   yc-disk-csi-node-v2-ck7dw            6/6     Running     0          15h
kube-system   coredns-768847b69f-hsv7q             1/1     Running     0          15h
kube-system   coredns-768847b69f-rxlzr             1/1     Running     0          15h
kube-system   hubble-generate-certs-928nm          0/1     Completed   0          18m
kube-system   hubble-relay-6cf7b87694-k6lll        1/1     Running     0          15h
kube-system   ip-masq-agent-j5bnb                  1/1     Running     0          15h
kube-system   ip-masq-agent-jxzgr                  1/1     Running     0          15h
kube-system   kube-dns-autoscaler-66b55897-c5vjn   1/1     Running     0          15h
kube-system   metrics-server-8689cb9795-msq67      1/1     Running     0          15h
kube-system   metrics-server-8689cb9795-nrtd2      1/1     Running     0          15h
kube-system   npd-v0.8.0-fr7c4                     1/1     Running     0          15h
kube-system   npd-v0.8.0-kw7hd                     1/1     Running     0          15h
kube-system   yc-disk-csi-node-v2-ck7dw            6/6     Running     0          15h
kube-system   hubble-relay-6cf7b87694-k6lll        1/1     Running     0          15h
kube-system   ip-masq-agent-j5bnb                  1/1     Running     0          15h
kube-system   ip-masq-agent-jxzgr                  1/1     Running     0          15h
kube-system   kube-dns-autoscaler-66b55897-c5vjn   1/1     Running     0          15h
kube-system   metrics-server-8689cb9795-msq67      1/1     Running     0          15h
kube-system   metrics-server-8689cb9795-nrtd2      1/1     Running     0          15h
kube-system   npd-v0.8.0-fr7c4                     1/1     Running     0          15h
kube-system   npd-v0.8.0-kw7hd                     1/1     Running     0          15h
kube-system   yc-disk-csi-node-v2-ck7dw            6/6     Running     0          15h
kube-system   npd-v0.8.0-fr7c4                     1/1     Running     0          15h
kube-system   npd-v0.8.0-kw7hd                     1/1     Running     0          15h
kube-system   yc-disk-csi-node-v2-ck7dw            6/6     Running     0          15h
kube-system   yc-disk-csi-node-v2-hjtlk            6/6     Running     0          15h
kube-system   yc-disk-csi-node-v2-hjtlk            6/6     Running     0          15h
kube-system   yc-disk-csi-node-v2-hjtlk            6/6     Running     0          15h 

## CPU/GPU node groups
resource "yandex_kubernetes_node_group" "gpu" {
  count     = var.enable_gpu ? 1 : 0
  cluster_id = yandex_kubernetes_cluster.this.id
  name       = "${var.project}-${var.env}-gpu"


# Этап 3 Docker + Kubernetes

## Логин в Registry:
yc container registry configure-docker
docker configured to use yc --profile "default" for authenticating "cr.yandex" container registries
Credential helper is configured in 'C:\Users\USER\.docker\config.json' 

## Build:
docker build -f docker/backend/Dockerfile -t cr.yandex/crpqca4kakrse7er8nvl/credit-backend:staging .
docker build -f docker/frontend/Dockerfile -t cr.yandex/crpqca4kakrse7er8nvl/credit-frontend:staging .

[+] Building 4.0s (23/23) FINISHED                                                docker:desktop-linux
 => [internal] load build definition from Dockerfile                                              0.0s
 => => transferring dockerfile: 1.47kB                                                            0.0s
 => resolve image config for docker-image://docker.io/docker/dockerfile:1                         2.4s
 => CACHED docker-image://docker.io/docker/dockerfile:1@sha256:b6afd42430b15f2d2a4c5a02b919e98a5  0.0s
 => => resolve docker.io/docker/dockerfile:1@sha256:b6afd42430b15f2d2a4c5a02b919e98a525b785b1aaf  0.0s
 => [internal] load metadata for docker.io/library/python:3.11-slim                               1.1s
 => [internal] load .dockerignore                                                                 0.0s
 => => transferring context: 293B                                                                 0.0s
 => [internal] load build context                                                                 0.0s
 => => transferring context: 604B                                                                 0.0s
 => [base 1/2] FROM docker.io/library/python:3.11-slim@sha256:158caf0e080e2cd74ef2879ed3c4e69779  0.0s
 => => resolve docker.io/library/python:3.11-slim@sha256:158caf0e080e2cd74ef2879ed3c4e697792ee65  0.0s
 => CACHED [base 2/2] WORKDIR /app                                                                0.0s
 => CACHED [dvc 1/7] RUN apt-get update && apt-get install -y --no-install-recommends ca-certifi  0.0s
 => CACHED [dvc 2/7] RUN pip install --no-cache-dir "dvc[s3]"                                     0.0s
 => CACHED [dvc 3/7] COPY .dvc/ ./.dvc/                                                           0.0s
 => CACHED [dvc 4/7] COPY .dvcignore dvc.yaml dvc.lock ./                                         0.0s
 => CACHED [dvc 5/7] COPY models/.gitignore ./models/.gitignore                                   0.0s
 => CACHED [dvc 6/7] COPY models/*.dvc ./models/                                                  0.0s
 => CACHED [dvc 7/7] RUN mkdir -p /app/models /app/data                                           0.0s
 => CACHED [runtime 1/4] RUN apt-get update && apt-get install -y --no-install-recommends libgom  0.0s
 => CACHED [runtime 2/4] COPY requirements.api.txt ./                                             0.0s
 => CACHED [builder 1/3] RUN apt-get update && apt-get install -y --no-install-recommends build-  0.0s
 => CACHED [builder 2/3] COPY requirements.txt requirements.api.txt ./                            0.0s
 => CACHED [builder 3/3] RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt -r  0.0s
 => CACHED [runtime 3/4] RUN --mount=type=bind,from=builder,source=/wheels,target=/wheels     pi  0.0s
 => CACHED [runtime 4/4] COPY app/ ./app                                                          0.0s
 => exporting to image                                                                            0.1s
 => => exporting layers                                                                           0.0s
 => => exporting manifest sha256:e58a63391aee492e6ec66e612769012d84c2b14309afaa9410265fc84c4d1fb  0.0s
 => => exporting config sha256:6d4bce410a21a16df65a0901ee5bff4ad4413fbcaedd48f3b502c147eca4dc45   0.0s 
 => => exporting attestation manifest sha256:6822c59ea09b2251cb8a3b3b682239d3453c33cb635f7368b84  0.0s 
 => => exporting manifest list sha256:7c260d710a661b3425c5a42995a2750139d0c38f7cf170e9296248f1fd  0.0s 
 => => naming to cr.yandex/crpqca4kakrse7er8nvl/credit-backend:staging                            0.0s
 => => unpacking to cr.yandex/crpqca4kakrse7er8nvl/credit-backend:staging                         0.0s 

 => [internal] load build definition from Dockerfile                                              0.0s
 => => transferring dockerfile: 458B                                                              0.0s 
 => resolve image config for docker-image://docker.io/docker/dockerfile:1                         0.3s 
 => CACHED docker-image://docker.io/docker/dockerfile:1@sha256:b6afd42430b15f2d2a4c5a02b919e98a5  0.0s
 => => resolve docker.io/docker/dockerfile:1@sha256:b6afd42430b15f2d2a4c5a02b919e98a525b785b1aaf  0.0s 
 => [internal] load metadata for docker.io/library/node:20-alpine                                 1.6s 
 => [internal] load metadata for docker.io/library/nginx:1.27-alpine                              1.6s 
 => [internal] load .dockerignore                                                                 0.0s
 => => transferring context: 293B                                                                 0.0s 
 => [builder 1/7] FROM docker.io/library/node:20-alpine@sha256:658d0f63e501824d6c23e06d4bb95c71e  0.0s 
 => => resolve docker.io/library/node:20-alpine@sha256:658d0f63e501824d6c23e06d4bb95c71e7d704537  0.0s 
 => [runtime 1/3] FROM docker.io/library/nginx:1.27-alpine@sha256:65645c7bb6a0661892a8b03b89d074  0.0s 
 => => resolve docker.io/library/nginx:1.27-alpine@sha256:65645c7bb6a0661892a8b03b89d0743208a18d  0.0s 
 => [internal] load build context                                                                 0.0s 
 => => transferring context: 9.45kB                                                               0.0s
 => CACHED [runtime 2/3] COPY docker/frontend/default.conf /etc/nginx/conf.d/default.conf         0.0s 
 => CACHED [builder 2/7] WORKDIR /frontend                                                        0.0s 
 => CACHED [builder 3/7] COPY frontend/package.json ./package.json                                0.0s 
 => CACHED [builder 4/7] COPY frontend/build.mjs ./build.mjs                                      0.0s 
 => CACHED [builder 5/7] COPY frontend/index.html ./index.html                                    0.0s 
 => CACHED [builder 6/7] RUN npm install --no-audit --no-fund                                     0.0s 
 => CACHED [builder 7/7] RUN npm run build                                                        0.0s 
 => CACHED [runtime 3/3] COPY --from=builder /frontend/dist/ /usr/share/nginx/html/               0.0s 
 => exporting to image                                                                            0.1s 
 => => exporting layers                                                                           0.0s 
 => => exporting manifest sha256:0a7865720cd9d31f8beccdc4b35eec90f6f6208677e18e64b95fefeac780c55  0.0s 
 => => exporting config sha256:b783d20f82aefdc1096d8a9d460588cae39a1ee2827407433633cd062e90bc19   0.0s 
 => => exporting attestation manifest sha256:4d20feb7387017302d065632b9accd5b7c85ab7d620c35303e0  0.0s 
 => => exporting manifest list sha256:59bf06fc3d25eedba7189952da132d61210b565109d6b0f994728e0006  0.0s 
 => => naming to cr.yandex/crpqca4kakrse7er8nvl/credit-frontend:staging                           0.0s
 => => unpacking to cr.yandex/crpqca4kakrse7er8nvl/credit-frontend:staging                        0.0s 

## Push:
docker push cr.yandex/crpqca4kakrse7er8nvl/credit-backend:staging
docker push cr.yandex/crpqca4kakrse7er8nvl/credit-frontend:staging
The push refers to repository [cr.yandex/crpqca4kakrse7er8nvl/credit-backend]
a2bdd8e6bf59: Pushed
45a423e543b9: Layer already exists
c8bd10fcc007: Layer already exists
4d55cfecf366: Layer already exists
84e029f3c1a2: Layer already exists
36fd98bc8114: Layer already exists
d8b1bdaefbb0: Layer already exists
1733a4cd5954: Layer already exists
76f8cc29836e: Layer already exists
72cf4c3b8301: Layer already exists
8cc5cbce1736: Layer already exists
3f0cdbca744e: Layer already exists
1cdf00629339: Layer already exists
cfa7b090f344: Layer already exists
896cfef3e2c4: Layer already exists
c93b465573f7: Layer already exists
0c59c369cd6d: Layer already exists
staging: digest: sha256:7c260d710a661b3425c5a42995a2750139d0c38f7cf170e9296248f1fd4bf524 size: 856

The push refers to repository [cr.yandex/crpqca4kakrse7er8nvl/credit-frontend]
695644136655: Pushed
34a64644b756: Layer already exists
6964eb51b3fa: Layer already exists
0bbe17d98fdf: Layer already exists
d7e507024086: Layer already exists
f18232174bc9: Layer already exists
61ca4f733c80: Layer already exists
81bd8ed7ec67: Layer already exists
b464cfdf2a63: Layer already exists
197eb75867ef: Layer already exists
39c2ddfd6010: Layer already exists
staging: digest: sha256:59bf06fc3d25eedba7189952da132d61210b565109d6b0f994728e0006a77ce6 size: 856 


## K8s apply
Namespace + ConfigMap:
kubectl apply -f k8s/00-namespace.yaml
kubectl apply -f k8s/10-configmap-backend.yaml 

## Деплой + сервисы + ingress: 
(.venv) PS C:\Users\USER\Desktop\credits-main> kubectl -n credit-scoring get secret s3-credentials
NAME             TYPE     DATA   AGE
s3-credentials   Opaque   2      28m
(.venv) PS C:\Users\USER\Desktop\credits-main> kubectl apply -f k8s/20-deploy-backend.yaml
deployment.apps/backend unchanged
(.venv) PS C:\Users\USER\Desktop\credits-main> kubectl apply -f k8s/21-svc-backend.yaml
service/backend-svc unchanged
(.venv) PS C:\Users\USER\Desktop\credits-main> kubectl apply -f k8s/30-deploy-frontend.yaml
deployment.apps/frontend unchanged
(.venv) PS C:\Users\USER\Desktop\credits-main> kubectl apply -f k8s/31-svc-frontend.yaml
service/frontend-svc unchanged
(.venv) PS C:\Users\USER\Desktop\credits-main> kubectl apply -f k8s/40-ingress.yaml
ingress.networking.k8s.io/backend-ingress unchanged
ingress.networking.k8s.io/frontend-ingress unchanged  

## Ingress Controller (через Helm):
(.venv) PS C:\Users\USER\Desktop\credits-main> helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
"ingress-nginx" has been added to your repositories
(.venv) PS C:\Users\USER\Desktop\credits-main> helm repo update
Hang tight while we grab the latest from your chart repositories...
...Successfully got an update from the "ingress-nginx" chart repository
Update Complete. ⎈Happy Helming!⎈
(.venv) PS C:\Users\USER\Desktop\credits-main> kubectl create namespace ingress-nginx --dry-run=client -o yaml | kubectl apply -f -
namespace/ingress-nginx unchanged
(.venv) PS C:\Users\USER\Desktop\credits-main> helm upgrade --install ingress-nginx ingress-nginx/ingress-nginx -n ingress-nginx
Release "ingress-nginx" does not exist. Installing it now.
NAME: ingress-nginx
LAST DEPLOYED: Thu Dec 18 12:50:35 2025
NAMESPACE: ingress-nginx
STATUS: deployed
REVISION: 1
DESCRIPTION: Install complete
TEST SUITE: None
NOTES:
The ingress-nginx controller has been installed.
It may take a few minutes for the load balancer IP to be available.
You can watch the status by running 'kubectl get service --namespace ingress-nginx ingress-nginx-controller --output wide --watch'

An example Ingress that makes use of the controller:
  apiVersion: networking.k8s.io/v1
  kind: Ingress
  metadata:
    name: example
    namespace: foo
  spec:
    ingressClassName: nginx
    rules:
      - host: www.example.com
        http:
          paths:
            - pathType: Prefix
              backend:
                service:
                  name: exampleService
                  port:
                    number: 80
              path: /
    # This section is only required if TLS is to be enabled for the Ingress
    tls:
      - hosts:
        - www.example.com
        secretName: example-tls

If TLS is enabled for the Ingress, a Secret containing the certificate and key must also be provided:  

  apiVersion: v1
  kind: Secret
  metadata:
    name: example-tls
    namespace: foo
  data:
    tls.crt: <base64 encoded cert>
    tls.key: <base64 encoded key>
  type: kubernetes.io/tls 

## Проверки
## Поды:
NAME                       READY   STATUS    RESTARTS   AGE    IP             NODE                     
   NOMINATED NODE   READINESS GATES
backend-756f546d5b-667rk   1/1     Running   0          33m    10.112.1.129   cl1qlcqt0anrnjsmic9v-owix   <none>           <none>
backend-756f546d5b-zgjfq   1/1     Running   0          34m    10.112.0.4     cl1qlcqt0anrnjsmic9v-ekof   <none>           <none>
frontend-9cb9d8c74-7zqzn   1/1     Running   0          110m   10.112.0.64    cl1qlcqt0anrnjsmic9v-ekof   <none>           <none> 


## Проверка наличия модели в runtime контейнере:
(.venv) PS C:\Users\USER\Desktop\credits-main> kubectl -n credit-scoring exec deploy/backend -c backend
 -- ls -la /app/models
total 324
drwxrwxrwx 3 root root   4096 Dec 18 09:17 .
drwxr-xr-x 1 root root   4096 Dec 18 09:13 ..
-rw-r--r-- 1 root root 315997 Dec 18 09:17 credit_default_model.pkl
drwxr-xr-x 2 root root   4096 Dec 18 09:17 processed 

## Ingress ресурсы:
(.venv) PS C:\Users\USER\Desktop\credits-main> kubectl -n credit-scoring get ingress
NAME               CLASS   HOSTS   ADDRESS          PORTS   AGE
backend-ingress    nginx   *       158.160.208.83   80      35m
frontend-ingress   nginx   *       158.160.208.83   80      35m 

## Внешний IP ingress-nginx:
(.venv) PS C:\Users\USER\Desktop\credits-main> kubectl -n credit-scoring get ingress                   NAME               CLASS   HOSTS   ADDRESS          PORTS   AGE                                        
backend-ingress    nginx   *       158.160.208.83   80      35m
frontend-ingress   nginx   *       158.160.208.83   80      35m 

## HTTP проверки:
(.venv) PS C:\Users\USER\Desktop\credits-main> curl http://158.160.208.83/api/health


StatusCode        : 200
StatusDescription : OK
Content           : {"status":"ok","model":"/app/models/credit_default_model.pkl"}
RawContent        : HTTP/1.1 200 OK
                    Connection: keep-alive
                    Content-Length: 62
                    Content-Type: application/json
                    Date: Thu, 18 Dec 2025 09:54:03 GMT

                    {"status":"ok","model":"/app/models/credit_default_model.pkl"}
Forms             : {}
Headers           : {[Connection, keep-alive], [Content-Length, 62], [Content-Type, application/json], 
                     [Date, Thu, 18 Dec 2025 09:54:03 GMT]}
Images            : {}
InputFields       : {}
Links             : {}
ParsedHtml        : mshtml.HTMLDocumentClass
RawContentLength  : 62 

(.venv) PS C:\Users\USER\Desktop\credits-main>  curl http://158.160.208.83/api/docs


StatusCode        : 200
StatusDescription : OK
Content           :
                        <!DOCTYPE html>
                        <html>
                        <head>
                        <link type="text/css" rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swag 
                    ger-ui-dist@5/swagger-ui.css">
                        <link rel="shortcut icon" href="https://...
RawContent        : HTTP/1.1 200 OK
                    Connection: keep-alive
                    Content-Length: 942
                    Content-Type: text/html; charset=utf-8
                    Date: Thu, 18 Dec 2025 09:55:46 GMT


                        <!DOCTYPE html>
                        <html>
                        <head>
                        <link type="...
Forms             : {}
Headers           : {[Connection, keep-alive], [Content-Length, 942], [Content-Type, text/html; charse 
                    t=utf-8], [Date, Thu, 18 Dec 2025 09:55:46 GMT]}
Images            : {}
InputFields       : {}
Links             : {}
ParsedHtml        : mshtml.HTMLDocumentClass
RawContentLength  : 942 

