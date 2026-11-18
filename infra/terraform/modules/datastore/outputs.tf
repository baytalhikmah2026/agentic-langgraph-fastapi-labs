output "address" {
  description = "host:port inside the cluster"
  value       = "${kubernetes_service_v1.this.metadata[0].name}.${var.namespace}.svc.cluster.local:${var.port}"
}
