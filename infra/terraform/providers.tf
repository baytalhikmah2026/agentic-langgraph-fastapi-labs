# How Terraform reaches the cluster (Lab 96): the same kubeconfig and context as kubectl
provider "kubernetes" {
  config_path    = var.kubeconfig
  config_context = var.kube_context
}

provider "helm" {
  kubernetes = {
    config_path    = var.kubeconfig
    config_context = var.kube_context
  }
}
