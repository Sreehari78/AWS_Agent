"""
Terraform configuration for the EKS Upgrade Agent.
"""

from typing import Optional
from pydantic import BaseModel, Field


class TerraformConfig(BaseModel):
    """Terraform configuration."""
    
    binary_path: str = Field(default="terraform", description="Path to terraform binary")
    working_directory: str = Field(default="./terraform", description="Terraform working directory")
    state_backend: str = Field(default="s3", description="Terraform state backend")
    state_bucket: Optional[str] = Field(None, description="S3 bucket for state")
    state_key_prefix: str = Field(
        default="eks-upgrade-agent/", description="S3 key prefix for state"
    )
    state_region: str = Field(default="us-east-1", description="AWS region for state")
    lock_table: Optional[str] = Field(None, description="DynamoDB table for state locking")
    auto_approve: bool = Field(default=False, description="Auto-approve terraform apply")
    parallelism: int = Field(default=10, description="Terraform parallelism")