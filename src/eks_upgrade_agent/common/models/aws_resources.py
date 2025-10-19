"""
AWS resource models for EKS components.
"""

from datetime import datetime, UTC
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .enums import AddonStatus, ApplicationStatus, NodeGroupStatus, SeverityLevel


class NodeGroupInfo(BaseModel):
    """Information about an EKS node group."""

    name: str = Field(..., description="Node group name")
    status: NodeGroupStatus = Field(..., description="Current node group status")
    instance_types: List[str] = Field(..., description="EC2 instance types used")
    ami_type: str = Field(..., description="AMI type (AL2_x86_64, AL2_ARM_64, etc.)")
    capacity_type: str = Field(..., description="Capacity type (ON_DEMAND, SPOT)")
    scaling_config: Dict[str, int] = Field(..., description= "Min/max/desired capacity")
    kubernetes_version: str = Field(..., description="Kubernetes version")
    launch_template: Optional[Dict[str, Any]] = Field(
        None, description="Launch template config"
    )
    remote_access: Optional[Dict[str, Any]] = Field(
        None, description="Remote access config"
    )
    labels: Dict[str, str] = Field(default_factory=dict, description="Node labels")
    taints: List[Dict[str, Any]] = Field(default_factory=list, description="Node taints")
    tags: Dict[str, str] = Field(default_factory=dict, description="Resource tags")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    modified_at: Optional[datetime] = Field(
        None, description="Last modification timestamp"
    )

    class Config:
        use_enum_values = True


class AddonInfo(BaseModel):
    """Information about an EKS addon."""

    name: str = Field(..., description="Addon name")
    status: AddonStatus = Field(..., description="Current addon status")
    version: str = Field(..., description="Addon version")
    service_account_role_arn: Optional[str] = Field(
        None, description="Service account IAM role"
    )
    configuration_values: Optional[str] = Field(None, description="JSON configuration")
    resolve_conflicts: Optional[str] = Field(
        None, description="Conflict resolution strategy"
    )
    tags: Dict[str, str] = Field(default_factory=dict, description="Resource tags")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    modified_at: Optional[datetime] = Field(
        None, description="Last modification timestamp"
    )

    class Config:
        use_enum_values = True


class ApplicationInfo(BaseModel):
    """Information about a deployed application."""

    name: str = Field(..., description="Application name")
    namespace: str = Field(..., description="Kubernetes namespace")
    status: ApplicationStatus = Field(..., description="Application status")
    version: str = Field(..., description="Application version")
    chart_name: Optional[str] = Field(None, description="Helm chart name")
    chart_version: Optional[str] = Field(None, description="Helm chart version")
    repository: Optional[str] = Field(
        None, description="Chart repository or Git repo"
    )
    values: Dict[str, Any] = Field(
        default_factory=dict, description="Configuration values"
    )
    resources: List[Dict[str, Any]] = Field(
        default_factory=list, description="Kubernetes resources"
    )
    health_status: Optional[Dict[str, Any]] = Field(
        None, description="Health check results"
    )
    sync_status: Optional[Dict[str, Any]] = Field(
        None, description="GitOps sync status"
    )
    dependencies: List[str] = Field(
        default_factory=list, description="Application dependencies"
    )
    labels: Dict[str, str] = Field(
        default_factory=dict, description="Application labels"
    )
    annotations: Dict[str, str] = Field(
        default_factory=dict, description="Application annotations"
    )
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")

    class Config:
        use_enum_values = True


class DeprecatedAPIInfo(BaseModel):
    """Information about deprecated Kubernetes APIs."""

    api_version: str = Field(..., description="Deprecated API version")
    kind: str = Field(..., description="Kubernetes resource kind")
    name: str = Field(..., description="Resource name")
    namespace: Optional[str] = Field(None, description="Resource namespace")
    deprecated_in: str = Field(..., description="Kubernetes version where deprecated")
    removed_in: Optional[str] = Field(
        None, description="Kubernetes version where removed"
    )
    replacement_api: Optional[str] = Field(None, description="Replacement API version")
    severity: SeverityLevel = Field(..., description="Severity of the deprecation")
    source: str = Field(
        ..., description="Source of detection (live cluster, manifest)"
    )
    file_path: Optional[str] = Field(None, description="File path if from manifest")
    line_number: Optional[int] = Field(None, description="Line number in file")
    migration_guide: Optional[str] = Field(
        None, description="Migration guidance URL"
    )
    detected_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="Detection timestamp"
    )

    class Config:
        use_enum_values = True