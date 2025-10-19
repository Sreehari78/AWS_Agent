"""
Cluster state and infrastructure models.
"""

from datetime import datetime, UTC
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .aws_resources import AddonInfo, ApplicationInfo, DeprecatedAPIInfo, NodeGroupInfo
from .enums import SeverityLevel


class ClusterState(BaseModel):
    """Complete state information for an EKS cluster."""

    # Basic cluster information
    cluster_name: str = Field(..., description="EKS cluster name")
    cluster_arn: str = Field(..., description="EKS cluster ARN")
    current_version: str = Field(..., description="Current Kubernetes version")
    platform_version: str = Field(..., description="EKS platform version")
    status: str = Field(..., description="Cluster status")
    endpoint: str = Field(..., description="Cluster API endpoint")

    # Infrastructure components
    node_groups: List[NodeGroupInfo] = Field(
        default_factory=list, description="Node groups"
    )
    addons: List[AddonInfo] = Field(default_factory=list, description="EKS addons")

    # Applications and workloads
    applications: List[ApplicationInfo] = Field(
        default_factory=list, description="Deployed applications"
    )

    # Compatibility and deprecation information
    deprecated_apis: List[DeprecatedAPIInfo] = Field(
        default_factory=list, description="Deprecated APIs found"
    )

    # Network and security
    vpc_config: Dict[str, Any] = Field(
        default_factory=dict, description="VPC configuration"
    )
    security_groups: List[str] = Field(
        default_factory=list, description="Security group IDs"
    )

    # Configuration and metadata
    logging: Dict[str, Any] = Field(
        default_factory=dict, description="Logging configuration"
    )
    encryption_config: Optional[Dict[str, Any]] = Field(
        None, description="Encryption configuration"
    )
    identity: Optional[Dict[str, Any]] = Field(
        None, description="Identity provider configuration"
    )
    tags: Dict[str, str] = Field(default_factory=dict, description="Cluster tags")

    # Timestamps
    created_at: Optional[datetime] = Field(None, description="Cluster creation time")
    last_updated: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="Last state update"
    )

    # Health and metrics
    health_status: Optional[Dict[str, Any]] = Field(
        None, description="Overall health status"
    )
    resource_usage: Optional[Dict[str, Any]] = Field(
        None, description="Resource utilization"
    )

    # Dependencies and relationships
    dependent_services: List[Dict[str, Any]] = Field(
        default_factory=list, description="Dependent AWS services"
    )

    def get_total_nodes(self) -> int:
        """Get total number of nodes across all node groups."""
        return sum(ng.scaling_config.get("desired_capacity", 0) for ng in self.node_groups)

    def get_deprecated_api_count(self) -> int:
        """Get count of deprecated APIs by severity."""
        return len(self.deprecated_apis)

    def get_critical_deprecated_apis(self) -> List[DeprecatedAPIInfo]:
        """Get list of critical deprecated APIs."""
        return [
            api for api in self.deprecated_apis if api.severity == SeverityLevel.CRITICAL
        ]

    def has_blocking_issues(self) -> bool:
        """Check if cluster has issues that would block upgrade."""
        return len(self.get_critical_deprecated_apis()) > 0