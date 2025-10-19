"""
Kubernetes configuration for the EKS Upgrade Agent.
"""

from typing import Optional
from pydantic import BaseModel, Field


class KubernetesConfig(BaseModel):
    """Kubernetes configuration."""
    
    kubeconfig_path: Optional[str] = Field(None, description="Path to kubeconfig file")
    context: Optional[str] = Field(None, description="Kubernetes context to use")
    namespace: str = Field(default="default", description="Default namespace")
    timeout_seconds: int = Field(default=300, description="Kubernetes API timeout")
    retry_attempts: int = Field(default=3, description="Number of retry attempts")
    verify_ssl: bool = Field(default=True, description="Verify SSL certificates")