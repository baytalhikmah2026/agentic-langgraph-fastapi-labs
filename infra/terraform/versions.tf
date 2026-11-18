# Infrastructure as code (Lab 96): the exact tools and where Terraform keeps its notes
terraform {
  required_version = ">= 1.17.2, < 2.0.0"

  required_providers {
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "3.5.0"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "3.3.0"
    }
  }

  # The state (what Terraform built) lives in the cluster itself, in a Secret, and a Lease
  # locks it while someone runs Terraform, so two people can never change things at once
  backend "kubernetes" {
    secret_suffix  = "sovereign-platform"
    namespace      = "kube-system"
    config_path    = "~/.kube/config"
    config_context = "kind-sovereign"
  }
}
