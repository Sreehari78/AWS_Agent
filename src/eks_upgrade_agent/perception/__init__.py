"""
Perception module for the EKS Upgrade Agent.

This module handles data collection from various sources including AWS APIs,
Kubernetes clusters, release notes, and deprecation scanning tools.
"""

from .aws_collector import AWSCollector
from .k8s_collector import KubernetesCollector
from .release_notes_collector import ReleaseNotesCollector
from .deprecation_scanner import DeprecationScanner

__all__ = [
    "AWSCollector",
    "KubernetesCollector", 
    "ReleaseNotesCollector",
    "DeprecationScanner",
]