# ⚠️  INTENTIONALLY INSECURE — for demonstration purposes only
# Run: python reviewer.py samples/insecure.tf

provider "aws" {
  region = "us-east-1"
}

# S3 bucket with public access and no encryption
resource "aws_s3_bucket" "data" {
  bucket = "my-company-data-bucket"
  acl    = "public-read"  # PUBLIC — anyone can read this bucket
}

resource "aws_s3_bucket_server_side_encryption_configuration" "data" {
  # MISSING — no encryption configured
}

# Overly permissive security group
resource "aws_security_group" "web" {
  name        = "web-sg"
  description = "Web server security group"

  ingress {
    description = "SSH from anywhere"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]  # OPEN TO WORLD
  }

  ingress {
    description = "RDP from anywhere"
    from_port   = 3389
    to_port     = 3389
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]  # OPEN TO WORLD
  }

  ingress {
    description = "Database"
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]  # DATABASE EXPOSED TO INTERNET
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# IAM role with admin access
resource "aws_iam_role" "app_role" {
  name = "app-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "admin" {
  role       = aws_iam_role.app_role.name
  policy_arn = "arn:aws:iam::aws:policy/AdministratorAccess"  # FULL ADMIN
}

# EC2 in public subnet, no IMDSv2
resource "aws_instance" "web" {
  ami                         = "ami-0c55b159cbfafe1f0"
  instance_type               = "t3.medium"
  subnet_id                   = aws_subnet.public.id
  associate_public_ip_address = true  # PUBLIC IP on production instance
  iam_instance_profile        = aws_iam_instance_profile.app.name

  # No IMDSv2 enforcement — vulnerable to SSRF-based credential theft
  metadata_options {
    http_endpoint = "enabled"
    http_tokens   = "optional"  # Should be "required"
  }

  # Hardcoded credentials in user_data
  user_data = <<-EOF
    #!/bin/bash
    export DB_PASSWORD="SuperSecret123!"
    export API_KEY="AKIAIOSFODNN7EXAMPLE"
    EOF

  tags = {
    Name = "web-server"
  }
}

# CloudTrail disabled
# MISSING — no aws_cloudtrail resource configured

# RDS with no encryption and publicly accessible
resource "aws_db_instance" "main" {
  identifier        = "prod-db"
  engine            = "postgres"
  instance_class    = "db.t3.medium"
  allocated_storage = 20
  username          = "admin"
  password          = "password123"  # HARDCODED PASSWORD

  publicly_accessible    = true   # DATABASE ON PUBLIC INTERNET
  storage_encrypted      = false  # NO ENCRYPTION AT REST
  deletion_protection    = false  # CAN BE DELETED ACCIDENTALLY
  skip_final_snapshot    = true
  backup_retention_period = 0     # NO BACKUPS
}
