variable "kubeconfig" {
  description = "The kubeconfig file kubectl uses"
  type        = string
  default     = "~/.kube/config"
}

variable "kube_context" {
  description = "The cluster to build in (kind names its context kind-<cluster>)"
  type        = string
  default     = "kind-sovereign"
}

variable "environment" {
  description = "The new environment's name; its namespace is sovereign-brain-<environment>"
  type        = string
  default     = "staging"
}

variable "registry" {
  description = "The bank's own image registry (Lab 91)"
  type        = string
  default     = "localhost:5001"
}

variable "postgres_password" {
  description = "PostgreSQL password for the new environment (set TF_VAR_postgres_password)"
  type        = string
  sensitive   = true
}
