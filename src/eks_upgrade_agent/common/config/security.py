"""
Security configuration for the EKS Upgrade Agent.
"""

from typing import Optional
from pydantic import BaseModel, Field


class SecurityConfig(BaseModel):
    """Security configuration."""
    
    use_ssm_parameters: bool = Field(default=True, description="Use AWS SSM for secrets")
    ssm_parameter_prefix: str = Field(
        default="/eks-upgrade-agent/",
        description="SSM parameter prefix"
    )
    encrypt_sensitive_data: bool = Field(default=True, description="Encrypt sensitive data")
    kms_key_id: Optional[str] = Field(None, description="KMS key ID for encryption")
    credential_rotation_enabled: bool = Field(
        default=False, description="Enable credential rotation"
    )
    credential_rotation_interval_hours: int = Field(
        default=24, description="Credential rotation interval in hours"
    )