resource "terraform_data" "production_deployment" {
  triggers_replace = [
    var.deploy_revision
  ]

  connection {
    type        = "ssh"
    host        = var.ssh_host
    user        = var.ssh_user
    private_key = file(var.ssh_private_key_path)
    timeout     = "2m"
  }

  provisioner "remote-exec" {
    inline = [
      "cd /home/ubuntu/pipeline",
      "docker compose -p pipeline-prod -f docker-compose.prod.yml config --quiet",
      "docker compose -p pipeline-prod -f docker-compose.prod.yml up -d",
      "docker compose -p pipeline-prod -f docker-compose.prod.yml ps"
    ]
  }
}