# The platform (Lab 96): what the infrastructure team owns, written as code.
# 1. The gate (Traefik) that Lab 87 installed by hand, now managed by Terraform.
# 2. A new, empty environment for the desk: a sealed namespace with quotas and its data stores.
# The desk's applications stay with Kustomize and Argo Rollouts (the application team's side).

locals {
  namespace = "sovereign-brain-${var.environment}"
  labels = {
    "app.kubernetes.io/part-of"      = "sovereign-brain"
    "crescent-ledger.bank/env"       = var.environment
    "crescent-ledger.bank/residency" = "on-premises"
  }
}

# 1. The gate. "import" adopts the release that already runs instead of installing a second one.
import {
  to = helm_release.traefik
  id = "traefik/traefik"
}

resource "helm_release" "traefik" {
  name       = "traefik"
  namespace  = "traefik"
  repository = "https://traefik.github.io/charts"
  chart      = "traefik"
  version    = "42.3.1"
  values     = [file("${path.module}/../../k8s/addons/traefik-values.yaml")]
}

# 2. A sealed namespace for the new environment
resource "kubernetes_namespace_v1" "desk" {
  metadata {
    name   = local.namespace
    labels = local.labels
  }
}

resource "kubernetes_resource_quota_v1" "desk" {
  metadata {
    name      = "desk-quota"
    namespace = kubernetes_namespace_v1.desk.metadata[0].name
  }
  spec {
    hard = {
      "requests.cpu"           = "4"
      "requests.memory"        = "8Gi"
      "limits.memory"          = "16Gi"
      "persistentvolumeclaims" = "10"
      "pods"                   = "30"
    }
  }
}

resource "kubernetes_limit_range_v1" "desk" {
  metadata {
    name      = "desk-defaults"
    namespace = kubernetes_namespace_v1.desk.metadata[0].name
  }
  spec {
    limit {
      type = "Container"
      default_request = {
        cpu    = "100m"
        memory = "128Mi"
      }
      default = {
        memory = "512Mi"
      }
    }
  }
}

resource "kubernetes_network_policy_v1" "no_internet" {
  metadata {
    name      = "no-internet"
    namespace = kubernetes_namespace_v1.desk.metadata[0].name
  }
  spec {
    pod_selector {}
    policy_types = ["Egress"]
    egress {
      to {
        pod_selector {}
      }
    }
    egress {
      to {
        namespace_selector {
          match_labels = { "kubernetes.io/metadata.name" = "kube-system" }
        }
        pod_selector {
          match_labels = { "k8s-app" = "kube-dns" }
        }
      }
      ports {
        port     = "53"
        protocol = "UDP"
      }
      ports {
        port     = "53"
        protocol = "TCP"
      }
    }
  }
}

resource "kubernetes_secret_v1" "postgres" {
  metadata {
    name      = "postgres-credentials"
    namespace = kubernetes_namespace_v1.desk.metadata[0].name
  }
  data = {
    POSTGRES_PASSWORD = var.postgres_password
  }
}

# The data stores: one module, used twice (Lab 85's warehouses, as code)
module "postgres" {
  source          = "./modules/datastore"
  name            = "postgres"
  namespace       = kubernetes_namespace_v1.desk.metadata[0].name
  image           = "${var.registry}/postgres:18.6"
  port            = 5432
  data_path       = "/var/lib/postgresql"
  storage         = "5Gi"
  probe_command   = ["pg_isready", "-U", "sb", "-d", "sovereign_brain"]
  env             = { POSTGRES_USER = "sb", POSTGRES_DB = "sovereign_brain" }
  password_secret = kubernetes_secret_v1.postgres.metadata[0].name
  password_env    = "POSTGRES_PASSWORD"
  labels          = local.labels
}

module "redis" {
  source        = "./modules/datastore"
  name          = "redis"
  namespace     = kubernetes_namespace_v1.desk.metadata[0].name
  image         = "${var.registry}/redis:8.10.3"
  port          = 6379
  data_path     = "/data"
  storage       = "1Gi"
  args          = ["redis-server", "--appendonly", "yes"]
  probe_command = ["redis-cli", "ping"]
  labels        = local.labels
}
