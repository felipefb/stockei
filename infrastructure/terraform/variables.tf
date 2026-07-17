variable "aws_region" {
  default = "sa-east-1"
}

variable "azs" {
  default = ["sa-east-1a", "sa-east-1b"]
}

variable "environment" {
  default = "mvp"
}

variable "db_username" {
  sensitive = true
}

variable "db_password" {
  sensitive = true
}
