variable "ssh_host" {
  type        = string
  description = "Adresse IP de la VM"
}

variable "ssh_user" {
  type    = string
  default = "ubuntu"
}

variable "ssh_private_key_path" {
  type        = string
  description = "Chemin de la clé SSH privée"
}

variable "deploy_revision" {
  type        = string
  description = "Version à déployer"
}