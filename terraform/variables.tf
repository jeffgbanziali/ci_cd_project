
variable "ssh_host" {
  type        = string
  description = "Adresse IP de la VM"
}

variable "ssh_user" {
  type        = string
  default     = "ubuntu"
  description = "Utilisateur SSH de la VM"
}

variable "ssh_password" {
  type        = string
  sensitive   = true
  description = "Mot de passe SSH de la VM de production"
}

variable "deploy_revision" {
  type        = string
  description = "Version à déployer"
}
