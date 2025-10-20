"""Pattern definitions for Kubernetes and EKS terminology."""

from enum import Enum
from typing import Dict, List


class ClassificationCategory(Enum):
    """Categories for Kubernetes text classification."""
    BREAKING_CHANGE = "BREAKING_CHANGE"
    DEPRECATION = "DEPRECATION"
    MIGRATION_REQUIRED = "MIGRATION_REQUIRED"
    SECURITY_UPDATE = "SECURITY_UPDATE"
    FEATURE_ADDITION = "FEATURE_ADDITION"
    BUG_FIX = "BUG_FIX"
    PERFORMANCE_IMPROVEMENT = "PERFORMANCE_IMPROVEMENT"
    CONFIGURATION_CHANGE = "CONFIGURATION_CHANGE"
    UNKNOWN = "UNKNOWN"


class SeverityLevel(Enum):
    """Severity levels for classification results."""
    CRITICAL = "CRITICAL"  # Immediate action required
    HIGH = "HIGH"         # Action required before upgrade
    MEDIUM = "MEDIUM"     # Action recommended
    LOW = "LOW"          # Informational
    INFO = "INFO"        # No action needed


class KubernetesPatterns:
    """Kubernetes-specific entity patterns."""

    ENTITY_PATTERNS = {
        "API_VERSION": [
            r"v\d+(?:alpha\d+|beta\d+)?",  # v1, v1alpha1, v1beta1
            r"apps/v\d+",  # apps/v1
            r"extensions/v\d+beta\d+",  # extensions/v1beta1
            r"networking\.k8s\.io/v\d+",  # networking.k8s.io/v1
            r"apiextensions\.k8s\.io/v\d+",  # apiextensions.k8s.io/v1
        ],
        "RESOURCE_KIND": [
            r"\b(?:Deployment|Service|Pod|ConfigMap|Secret|Ingress|StatefulSet|DaemonSet|Job|CronJob|PersistentVolume|PersistentVolumeClaim|ServiceAccount|Role|RoleBinding|ClusterRole|ClusterRoleBinding|NetworkPolicy|PodSecurityPolicy|CustomResourceDefinition|HorizontalPodAutoscaler|VerticalPodAutoscaler)\b",
        ],
        "BREAKING_CHANGE_INDICATORS": [
            r"\b(?:deprecated|removed|breaking change|incompatible|migration required|no longer supported)\b",
            r"\b(?:BREAKING|DEPRECATED|REMOVED)\b",
        ],
        "VERSION_NUMBER": [
            r"\b\d+\.\d+(?:\.\d+)?(?:-\w+(?:\.\d+)?)?\b",  # 1.27.0, 1.28.0-alpha.1
        ],
        "EKS_COMPONENT": [
            r"\b(?:kube-proxy|coredns|vpc-cni|aws-load-balancer-controller|cluster-autoscaler|ebs-csi-driver|efs-csi-driver)\b",
        ]
    }

    CONFIDENCE_THRESHOLDS = {
        "PERSON": 0.8,
        "LOCATION": 0.7,
        "ORGANIZATION": 0.7,
        "COMMERCIAL_ITEM": 0.6,
        "EVENT": 0.6,
        "DATE": 0.8,
        "QUANTITY": 0.7,
        "TITLE": 0.6,
        "OTHER": 0.5,
        # Custom Kubernetes entities
        "API_VERSION": 0.9,
        "RESOURCE_KIND": 0.8,
        "BREAKING_CHANGE": 0.7,
        "VERSION_NUMBER": 0.8,
        "EKS_COMPONENT": 0.8,
    }


class ClassificationPatterns:
    """Classification patterns with associated categories and severities."""

    PATTERNS = {
        ClassificationCategory.BREAKING_CHANGE: {
            "patterns": [
                r"\b(?:breaking change|incompatible|no longer supported|removed in|will be removed)\b",
                r"\bBREAKING\b",
                r"\b(?:incompatible with|breaks compatibility)\b",
                r"\b(?:major version|breaking API)\b"
            ],
            "severity": SeverityLevel.CRITICAL,
            "keywords": ["breaking", "incompatible", "removed", "unsupported"]
        },
        ClassificationCategory.DEPRECATION: {
            "patterns": [
                r"\b(?:deprecated|deprecation|will be deprecated)\b",
                r"\bDEPRECATED\b",
                r"\b(?:marked for removal|scheduled for removal)\b",
                r"\b(?:legacy|obsolete)\b"
            ],
            "severity": SeverityLevel.HIGH,
            "keywords": ["deprecated", "deprecation", "legacy", "obsolete"]
        },
        ClassificationCategory.MIGRATION_REQUIRED: {
            "patterns": [
                r"\b(?:migration required|must migrate|migrate to|update to)\b",
                r"\b(?:action required|manual intervention)\b",
                r"\b(?:upgrade path|migration guide)\b"
            ],
            "severity": SeverityLevel.HIGH,
            "keywords": ["migration", "migrate", "action required", "manual"]
        },
        ClassificationCategory.SECURITY_UPDATE: {
            "patterns": [
                r"\b(?:security|vulnerability|CVE-\d+|security fix|security patch)\b",
                r"\b(?:exploit|malicious|attack|breach)\b",
                r"\b(?:authentication|authorization|privilege)\b"
            ],
            "severity": SeverityLevel.CRITICAL,
            "keywords": ["security", "vulnerability", "CVE", "exploit"]
        },
        ClassificationCategory.CONFIGURATION_CHANGE: {
            "patterns": [
                r"\b(?:configuration|config|setting|parameter|flag)\b",
                r"\b(?:default value|default behavior)\b",
                r"\b(?:environment variable|env var)\b"
            ],
            "severity": SeverityLevel.MEDIUM,
            "keywords": ["configuration", "config", "setting", "default"]
        },
        ClassificationCategory.FEATURE_ADDITION: {
            "patterns": [
                r"\b(?:new feature|added|introduced|enhancement)\b",
                r"\b(?:support for|now supports|enables)\b",
                r"\b(?:improvement|optimization)\b"
            ],
            "severity": SeverityLevel.INFO,
            "keywords": ["new", "added", "introduced", "enhancement"]
        }
    }


class KubernetesComponents:
    """Kubernetes component definitions."""

    COMPONENTS = {
        "API_OBJECTS": [
            "Deployment", "Service", "Pod", "ConfigMap", "Secret", "Ingress",
            "StatefulSet", "DaemonSet", "Job", "CronJob", "PersistentVolume",
            "PersistentVolumeClaim", "ServiceAccount", "Role", "RoleBinding",
            "ClusterRole", "ClusterRoleBinding", "NetworkPolicy", "PodSecurityPolicy"
        ],
        "API_GROUPS": [
            "apps", "extensions", "networking.k8s.io", "rbac.authorization.k8s.io",
            "apiextensions.k8s.io", "autoscaling", "batch", "policy"
        ],
        "EKS_ADDONS": [
            "vpc-cni", "coredns", "kube-proxy", "aws-load-balancer-controller",
            "cluster-autoscaler", "ebs-csi-driver", "efs-csi-driver"
        ]
    }