variable "name" {
  description = "Name of the StatefulSet and its headless Service"
  type        = string
}

variable "namespace" {
  type = string
}

variable "image" {
  type = string
}

variable "port" {
  type = number
}

variable "data_path" {
  description = "Where the data lives inside the container"
  type        = string
}

variable "storage" {
  description = "Size of the data disk"
  type        = string
}

variable "probe_command" {
  description = "Command that succeeds when the store can serve (readiness and liveness)"
  type        = list(string)
}

variable "args" {
  type    = list(string)
  default = []
}

variable "env" {
  description = "Plain settings for the container"
  type        = map(string)
  default     = {}
}

variable "password_secret" {
  description = "Secret that holds the password (null: no password variable)"
  type        = string
  default     = null
}

variable "password_env" {
  description = "Name of the password variable and of its key in the Secret"
  type        = string
  default     = null
}

variable "labels" {
  type = map(string)
}
