"""
Example demonstrating Amazon Bedrock integration for EKS upgrade analysis.

This example shows how to use the BedrockClient to analyze release notes
and make upgrade decisions using Claude 3 Sonnet.
"""

import asyncio
from src.eks_upgrade_agent.common.aws_ai import BedrockClient
from src.eks_upgrade_agent.common.models.aws_ai import AWSAIConfig


def main():
    """Demonstrate Bedrock integration capabilities."""
    
    # Configure AWS AI services
    config = AWSAIConfig(
        bedrock_model_id="anthropic.claude-3-sonnet-20240229-v1:0",
        bedrock_region="us-east-1",
        max_bedrock_requests_per_minute=10,
        cost_threshold_usd=50.0,
        bedrock_temperature=0.1,
    )
    
    # Initialize Bedrock client
    client = BedrockClient(config)
    
    # Example release notes for analysis
    sample_release_notes = """
    Kubernetes v1.28 Release Notes
    
    Major Changes:
    - API version batch/v1beta1 for CronJob is deprecated
    - PodSecurityPolicy is removed (use Pod Security Standards)
    - Legacy service account token secrets are disabled by default
    
    New Features:
    - Enhanced node lifecycle management
    - Improved container runtime security
    - Better resource allocation for system pods
    
    Breaking Changes:
    - Removed support for dockershim
    - Changed default behavior for service account tokens
    """
    
    try:
        print("🔍 Analyzing release notes with Bedrock...")
        
        # Analyze release notes
        analysis_result = client.analyze_release_notes(
            release_notes=sample_release_notes,
            source_version="1.27",
            target_version="1.28"
        )
        
        print(f"\n📊 Analysis Results:")
        print(f"Analysis ID: {analysis_result.analysis_id}")
        print(f"Severity Score: {analysis_result.severity_score}/10")
        print(f"Confidence: {analysis_result.confidence}")
        
        print(f"\n🔍 Key Findings:")
        for finding in analysis_result.findings:
            print(f"  • {finding}")
        
        print(f"\n⚠️  Breaking Changes:")
        for change in analysis_result.breaking_changes:
            print(f"  • {change}")
        
        print(f"\n📋 Deprecations:")
        for deprecation in analysis_result.deprecations:
            print(f"  • {deprecation}")
        
        print(f"\n💡 Recommendations:")
        for recommendation in analysis_result.recommendations:
            print(f"  • {recommendation}")
        
        # Example cluster state for decision making
        cluster_state = """
        EKS Cluster: production-cluster
        Current Version: 1.27.8
        Node Groups: 3 (mixed instance types)
        Workloads: 45 deployments, 12 statefulsets
        Critical Services: API gateway, database, monitoring
        Recent Issues: None in last 30 days
        """
        
        print(f"\n🤔 Making upgrade decision...")
        
        # Make upgrade decision
        decision_result = client.make_upgrade_decision(
            cluster_state=cluster_state,
            analysis_results=[analysis_result],
            target_version="1.28"
        )
        
        print(f"\n🎯 Upgrade Decision:")
        print(f"Decision Severity: {decision_result.severity_score}/10")
        print(f"Confidence: {decision_result.confidence}")
        
        print(f"\n📋 Decision Factors:")
        for finding in decision_result.findings:
            print(f"  • {finding}")
        
        print(f"\n🚨 Critical Issues:")
        for issue in decision_result.breaking_changes:
            print(f"  • {issue}")
        
        print(f"\n📝 Action Items:")
        for recommendation in decision_result.recommendations:
            print(f"  • {recommendation}")
        
        # Show cost summary
        cost_summary = client.get_cost_summary()
        print(f"\n💰 Cost Summary:")
        print(f"Daily Cost: ${cost_summary['daily_cost_usd']:.4f}")
        print(f"Requests (last minute): {cost_summary['requests_last_minute']}")
        print(f"Rate Limit: {cost_summary['rate_limit']} req/min")
        
        # Determine recommendation based on severity
        if decision_result.severity_score <= 3:
            recommendation = "✅ PROCEED - Low risk upgrade"
        elif decision_result.severity_score <= 6:
            recommendation = "⚠️  PROCEED WITH CAUTION - Medium risk, additional validation recommended"
        elif decision_result.severity_score <= 8:
            recommendation = "🛑 HALT - High risk, significant preparation required"
        else:
            recommendation = "🚨 HALT - Critical risk, major changes needed before upgrade"
        
        print(f"\n🎯 Final Recommendation: {recommendation}")
        
    except Exception as e:
        print(f"❌ Error during analysis: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())