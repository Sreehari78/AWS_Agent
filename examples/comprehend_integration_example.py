#!/usr/bin/env python3
"""
Example demonstrating Amazon Comprehend integration for EKS Upgrade Agent.

This example shows how to use the Comprehend client to analyze Kubernetes
release notes and extract breaking changes, deprecations, and action items.
"""

import asyncio
import json
from pathlib import Path

from src.eks_upgrade_agent.common.models.aws_ai import AWSAIConfig
from src.eks_upgrade_agent.common.aws.comprehend import ComprehendClient


def main():
    """Main example function."""
    print("🔍 Amazon Comprehend Integration Example")
    print("=" * 50)
    
    # Initialize configuration
    config = AWSAIConfig(
        comprehend_region="us-east-1",
        comprehend_language_code="en",
        max_comprehend_requests_per_minute=100,
        # Use default AWS credentials from environment/profile
        aws_profile=None  # Set to your AWS profile if needed
    )
    
    # Sample Kubernetes release notes text
    sample_release_notes = """
    Kubernetes v1.28 Release Notes
    
    BREAKING CHANGES:
    - The v1beta1 Ingress API has been removed. All Ingress resources must use networking.k8s.io/v1.
    - PodSecurityPolicy is deprecated and will be removed in v1.29. Migrate to Pod Security Standards.
    - The extensions/v1beta1 Deployment API is no longer supported.
    
    DEPRECATIONS:
    - The kubectl run --generator flag is deprecated and will be removed.
    - Legacy service account token secrets are deprecated.
    
    SECURITY UPDATES:
    - Fixed CVE-2023-1234: Container escape vulnerability in kubelet
    - Updated kube-proxy to address privilege escalation issue
    
    NEW FEATURES:
    - Added support for sidecar containers in Pod spec
    - Enhanced cluster autoscaler with new scaling policies
    - Improved vpc-cni performance and reliability
    
    CONFIGURATION CHANGES:
    - Default value for --feature-gates changed
    - New environment variables for coredns configuration
    """
    
    try:
        # Initialize Comprehend client
        print("🚀 Initializing Comprehend client...")
        client = ComprehendClient(config)
        
        # Example 1: Basic entity detection
        print("\n📋 Example 1: Basic Entity Detection")
        print("-" * 40)
        
        entities = client.detect_entities(sample_release_notes)
        print(f"Detected {len(entities)} entities:")
        
        for entity in entities[:5]:  # Show first 5 entities
            print(f"  - {entity.text} ({entity.type}) - Confidence: {entity.confidence:.2f}")
        
        # Example 2: Comprehensive Kubernetes analysis
        print("\n🔬 Example 2: Comprehensive Kubernetes Analysis")
        print("-" * 50)
        
        analysis = client.analyze_kubernetes_text(sample_release_notes)
        
        print(f"Analysis ID: {analysis['analysis_id']}")
        print(f"Processing time: {analysis['processing_time']:.2f} seconds")
        print(f"Kubernetes relevance score: {analysis['summary']['kubernetes_relevance_score']:.2f}")
        
        # Show entity summary
        entity_summary = analysis['entities']
        print(f"\nEntity Summary:")
        print(f"  - Comprehend entities: {len(entity_summary['comprehend_entities'])}")
        print(f"  - Kubernetes entities: {len(entity_summary['kubernetes_entities'])}")
        print(f"  - Filtered entities: {len(entity_summary['filtered_entities'])}")
        
        # Show classifications
        classifications = analysis['classifications']
        print(f"\nClassifications ({len(classifications)} found):")
        for classification in classifications:
            print(f"  - {classification['category']}: {classification['severity']} "
                  f"(confidence: {classification['confidence']:.2f})")
        
        # Show Kubernetes context
        k8s_context = analysis['kubernetes_context']
        print(f"\nKubernetes Context:")
        print(f"  - API objects: {', '.join(k8s_context['api_objects'][:5])}")
        print(f"  - EKS addons: {', '.join(k8s_context['eks_addons'])}")
        print(f"  - Version references: {', '.join(k8s_context['version_references'][:3])}")
        
        # Example 3: Breaking change detection
        print("\n⚠️  Example 3: Breaking Change Detection")
        print("-" * 45)
        
        breaking_changes = client.detect_breaking_changes(sample_release_notes)
        
        print(f"Breaking Changes Analysis:")
        print(f"  - Breaking changes found: {len(breaking_changes['breaking_changes'])}")
        print(f"  - API deprecations found: {len(breaking_changes['api_deprecations'])}")
        print(f"  - Critical actions required: {len(breaking_changes['critical_actions'])}")
        print(f"  - Overall severity score: {breaking_changes['severity_assessment']['overall_score']:.1f}/10")
        
        if breaking_changes['severity_assessment']['requires_immediate_action']:
            print("  ⚠️  IMMEDIATE ACTION REQUIRED!")
        
        if breaking_changes['severity_assessment']['migration_required']:
            print("  📋 MIGRATION REQUIRED!")
        
        # Show critical actions
        critical_actions = breaking_changes['critical_actions']
        if critical_actions:
            print(f"\nCritical Actions ({len(critical_actions)}):")
            for i, action in enumerate(critical_actions[:3], 1):
                print(f"  {i}. {action['action']}")
                print(f"     Category: {action['category']}, Severity: {action['severity']}")
                print(f"     Priority: {action['priority']:.2f}")
        
        # Example 4: Usage statistics
        print("\n📊 Example 4: Usage Statistics")
        print("-" * 35)
        
        stats = client.get_usage_statistics()
        rate_limiting = stats['rate_limiting']
        
        print(f"Rate Limiting:")
        print(f"  - Current requests: {rate_limiting['current_requests']}")
        print(f"  - Max per minute: {rate_limiting['max_requests_per_minute']}")
        print(f"  - Utilization: {rate_limiting['utilization_percentage']:.1f}%")
        print(f"  - Can make request: {rate_limiting['can_make_request']}")
        
        print(f"\nConfiguration:")
        config_info = stats['configuration']
        print(f"  - Region: {config_info['region']}")
        print(f"  - Language: {config_info['language_code']}")
        print(f"  - Client status: {stats['client_status']}")
        
        # Example 5: Save detailed results
        print("\n💾 Example 5: Saving Results")
        print("-" * 32)
        
        # Save comprehensive analysis to file
        output_file = Path("comprehend_analysis_results.json")
        with open(output_file, 'w') as f:
            json.dump(analysis, f, indent=2, default=str)
        
        print(f"Detailed analysis saved to: {output_file}")
        
        # Save breaking changes summary
        summary_file = Path("breaking_changes_summary.json")
        with open(summary_file, 'w') as f:
            json.dump(breaking_changes, f, indent=2, default=str)
        
        print(f"Breaking changes summary saved to: {summary_file}")
        
        print("\n✅ Comprehend integration example completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error during example execution: {e}")
        print("Make sure you have:")
        print("1. Valid AWS credentials configured")
        print("2. Comprehend service access in your AWS account")
        print("3. Proper IAM permissions for Comprehend")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())