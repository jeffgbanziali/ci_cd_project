
terraform {
  required_version = ">= 1.5.0"

  backend "local" {
    path = "C:/TerraformState/financial-pipeline/terraform.tfstate"
  }

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
  }
}
