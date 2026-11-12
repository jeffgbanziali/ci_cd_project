
resource "terraform_data" "production_deployment" {
  triggers_replace = [
    var.deploy_revision
  ]

  connection {
    type        = "ssh"
    host        = var.ssh_host
    user        = var.ssh_user
    password    = var.ssh_password
    timeout     = "5m"
    script_path = "/tmp/terraform_%RAND%.sh"
  }

  provisioner "remote-exec" {
    inline = [
      "cd /home/ubuntu/financial-pipeline/runtime",
      "docker compose -p financial-pipeline -f docker-compose.prod.yml config --quiet",
      "docker compose -p financial-pipeline -f docker-compose.prod.yml up -d --no-build",
      "docker compose -p financial-pipeline -f docker-compose.prod.yml ps"
    ]
  }
}
