output "namespace" {
  description = "Where the new environment lives"
  value       = kubernetes_namespace_v1.desk.metadata[0].name
}

output "data_stores" {
  description = "The in-cluster addresses of the new environment's data stores"
  value       = [module.postgres.address, module.redis.address]
}
