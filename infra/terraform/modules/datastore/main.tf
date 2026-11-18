# One data store (Lab 96): a StatefulSet with its own disk, on the bank's own node, behind
# a headless Service. The same shape as Lab 85's YAML, written once and reused.

locals {
  labels   = merge(var.labels, { "app.kubernetes.io/name" = var.name })
  selector = { "app.kubernetes.io/name" = var.name }
}

resource "kubernetes_service_v1" "this" {
  metadata {
    name      = var.name
    namespace = var.namespace
    labels    = local.labels
  }
  spec {
    cluster_ip = "None"
    selector   = local.selector
    port {
      name        = "main"
      port        = var.port
      target_port = var.port
    }
  }
}

resource "kubernetes_stateful_set_v1" "this" {
  metadata {
    name      = var.name
    namespace = var.namespace
    labels    = local.labels
  }

  spec {
    service_name = kubernetes_service_v1.this.metadata[0].name
    replicas     = 1

    persistent_volume_claim_retention_policy {
      when_deleted = "Retain"
      when_scaled  = "Retain"
    }

    selector {
      match_labels = local.selector
    }

    template {
      metadata {
        labels = local.labels
      }
      spec {
        node_selector = { "crescent-ledger.bank/residency" = "on-premises" }

        container {
          name  = var.name
          image = var.image
          args  = var.args

          port {
            name           = "main"
            container_port = var.port
          }

          dynamic "env" {
            for_each = var.env
            content {
              name  = env.key
              value = env.value
            }
          }

          dynamic "env" {
            for_each = var.password_secret == null ? [] : [var.password_env]
            content {
              name = env.value
              value_from {
                secret_key_ref {
                  name = var.password_secret
                  key  = env.value
                }
              }
            }
          }

          readiness_probe {
            exec {
              command = var.probe_command
            }
            period_seconds = 5
          }

          liveness_probe {
            exec {
              command = var.probe_command
            }
            period_seconds    = 10
            failure_threshold = 6
          }

          resources {
            requests = {
              cpu    = "100m"
              memory = "256Mi"
            }
            limits = {
              memory = "1Gi"
            }
          }

          volume_mount {
            name       = "data"
            mount_path = var.data_path
          }
        }
      }
    }

    volume_claim_template {
      metadata {
        name = "data"
      }
      spec {
        access_modes = ["ReadWriteOnce"]
        resources {
          requests = {
            storage = var.storage
          }
        }
      }
    }
  }
}
