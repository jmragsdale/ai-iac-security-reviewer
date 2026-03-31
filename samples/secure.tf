# ✅  SECURE VERSION — remediated findings from insecure.tf
# All issues identified by ai-iac-security-reviewer have been fixed.

provider "aws" {
  region = "us-east-1"
}

# KMS key for encryption
resource "aws_kms_key" "data" {
  description             = "CMK for data bucket encryption"
  enable_key_rotation     = true
  deletion_window_in_days = 30
}

# S3 bucket — private, encrypted, versioned
resource "aws_s3_bucket" "data" {
  bucket = "my-company-data-bucket"
}

resource "aws_s3_bucket_acl" "data" {
  bucket = aws_s3_bucket.data.id
  acl    = "private"
}

resource "aws_s3_bucket_public_access_block" "data" {
  bucket                  = aws_s3_bucket.data.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "data" {
  bucket = aws_s3_bucket.data.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.data.arn
    }
  }
}

resource "aws_s3_bucket_versioning" "data" {
  bucket = aws_s3_bucket.data.id
  versioning_configuration {
    status = "Enabled"
  }
}

# Security group — least privilege, no public SSH/RDP
resource "aws_security_group" "web" {
  name        = "web-sg"
  description = "Web server security group — HTTPS only inbound"
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "HTTPS from internet"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # SSH only from bastion/VPN CIDR — never the internet
  ingress {
    description = "SSH from VPN/bastion only"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.vpn_cidr]
  }

  egress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTPS outbound only"
  }
}

# IAM role — least privilege, no admin
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

resource "aws_iam_policy" "app_policy" {
  name        = "app-least-privilege"
  description = "Minimal permissions for the app role"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["s3:GetObject", "s3:PutObject"]
        Resource = "${aws_s3_bucket.data.arn}/*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "app" {
  role       = aws_iam_role.app_role.name
  policy_arn = aws_iam_policy.app_policy.arn
}

# EC2 — private subnet, IMDSv2 enforced, no hardcoded credentials
resource "aws_instance" "web" {
  ami                         = "ami-0c55b159cbfafe1f0"
  instance_type               = "t3.medium"
  subnet_id                   = aws_subnet.private.id
  associate_public_ip_address = false
  iam_instance_profile        = aws_iam_instance_profile.app.name
  vpc_security_group_ids      = [aws_security_group.web.id]

  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required"  # IMDSv2 enforced
    http_put_response_hop_limit = 1
  }

  root_block_device {
    encrypted   = true
    kms_key_id  = aws_kms_key.data.arn
    volume_type = "gp3"
  }

  # Credentials injected at runtime via Secrets Manager — nothing hardcoded
  user_data = <<-EOF
    #!/bin/bash
    DB_PASSWORD=$(aws secretsmanager get-secret-value \
      --secret-id prod/db/password --query SecretString --output text)
    EOF

  tags = {
    Name = "web-server"
  }
}

# CloudTrail enabled
resource "aws_cloudtrail" "main" {
  name                          = "prod-trail"
  s3_bucket_name                = aws_s3_bucket.cloudtrail.id
  include_global_service_events = true
  is_multi_region_trail         = true
  enable_log_file_validation    = true

  event_selector {
    read_write_type           = "All"
    include_management_events = true
  }
}

# RDS — encrypted, private, backups enabled
resource "aws_db_instance" "main" {
  identifier        = "prod-db"
  engine            = "postgres"
  instance_class    = "db.t3.medium"
  allocated_storage = 20
  username          = "dbadmin"
  # Password injected from Secrets Manager via manage_master_user_password
  manage_master_user_password = true

  publicly_accessible        = false
  storage_encrypted          = true
  kms_key_id                 = aws_kms_key.data.arn
  deletion_protection        = true
  skip_final_snapshot        = false
  final_snapshot_identifier  = "prod-db-final-snapshot"
  backup_retention_period    = 7
  multi_az                   = true
  db_subnet_group_name       = aws_db_subnet_group.main.name
  vpc_security_group_ids     = [aws_security_group.db.id]

  enabled_cloudwatch_logs_exports = ["postgresql", "upgrade"]
}
