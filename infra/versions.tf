terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
  }
}

provider "aws" {
  region = var.region_aws
  # Sin credenciales aqui: se toman del entorno de AWS Academy
  # (AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY / AWS_SESSION_TOKEN) o del
  # archivo ~/.aws/credentials que genera el Learner Lab.
}
