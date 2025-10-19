"""
Prompt templates for Amazon Bedrock analysis and decision making.
"""


class PromptTemplates:
    """Collection of prompt templates for different analysis tasks."""

    RELEASE_NOTES_ANALYSIS = """
You are an expert Kubernetes and EKS engineer analyzing release notes for upgrade impact assessment.

**Task**: Analyze the following release notes to identify breaking changes, deprecations, and required actions for upgrading from version {source_version} to {target_version}.

**Release Notes**:
{release_notes}

**Instructions**:
1. Carefully read through the release notes
2. Identify any breaking changes that could affect existing workloads
3. Find API deprecations and their timelines
4. Note any required actions or migration steps
5. Assess the overall risk and complexity of the upgrade
6. Provide specific recommendations for preparation

**Output Format** (respond with valid JSON):
{{
    "findings": [
        "List of key findings from the release notes"
    ],
    "breaking_changes": [
        "Specific breaking changes that could impact existing workloads"
    ],
    "deprecations": [
        "API deprecations with timelines and replacement information"
    ],
    "recommendations": [
        "Specific actions to take before upgrading"
    ],
    "severity_score": 0.0-10.0,
    "confidence": 0.0-1.0
}}

**Severity Score Guidelines**:
- 0-2: Low risk, minor changes only
- 3-4: Low-medium risk, some deprecations but no breaking changes
- 5-6: Medium risk, some breaking changes or major deprecations
- 7-8: High risk, significant breaking changes affecting common use cases
- 9-10: Critical risk, major breaking changes affecting most workloads

Focus on practical impact for production EKS clusters running typical workloads (web applications, databases, monitoring tools, etc.).
"""

    UPGRADE_DECISION = """
You are an expert DevOps engineer making a critical decision about whether to proceed with an EKS cluster upgrade.

**Current Situation**:
- Target Version: {target_version}
- Cluster State: {cluster_state}

**Analysis Results**:
{analysis_summary}

**Task**: Based on the cluster state and analysis results, determine whether it's safe to proceed with the upgrade and what precautions should be taken.

**Decision Criteria**:
1. **Safety**: Are there any critical breaking changes that could cause outages?
2. **Compatibility**: Will existing workloads continue to function?
3. **Dependencies**: Are there any dependency conflicts or version mismatches?
4. **Risk Assessment**: What's the overall risk level of this upgrade?
5. **Mitigation**: What steps can reduce risks?

**Output Format** (respond with valid JSON):
{{
    "findings": [
        "Key decision factors and risk assessment"
    ],
    "breaking_changes": [
        "Critical issues that must be addressed before upgrade"
    ],
    "deprecations": [
        "Deprecation warnings and timeline concerns"
    ],
    "recommendations": [
        "Specific actions to take (proceed/halt/prepare)"
    ],
    "severity_score": 0.0-10.0,
    "confidence": 0.0-1.0
}}

**Decision Guidelines**:
- Severity 0-3: PROCEED - Low risk, standard precautions
- Severity 4-6: PROCEED WITH CAUTION - Medium risk, additional validation needed
- Severity 7-8: HALT - High risk, significant preparation required
- Severity 9-10: HALT - Critical risk, major changes needed before upgrade

Be conservative in your assessment - it's better to be overly cautious than to cause production outages.
"""

    DEPRECATION_IMPACT_ANALYSIS = """
You are a Kubernetes expert analyzing the impact of deprecated APIs on a cluster upgrade.

**Deprecated APIs Found**:
{deprecated_apis}

**Target Kubernetes Version**: {target_version}

**Task**: Analyze the impact of these deprecated APIs and provide migration guidance.

**Analysis Focus**:
1. Which APIs will stop working after the upgrade?
2. What are the replacement APIs or resources?
3. How complex is the migration for each deprecated resource?
4. What's the timeline for addressing these deprecations?
5. Are there any automated migration tools available?

**Output Format** (respond with valid JSON):
{{
    "findings": [
        "Summary of deprecation impact and urgency"
    ],
    "breaking_changes": [
        "APIs that will immediately break after upgrade"
    ],
    "deprecations": [
        "APIs deprecated but still functional (with timelines)"
    ],
    "recommendations": [
        "Step-by-step migration plan for each deprecated API"
    ],
    "severity_score": 0.0-10.0,
    "confidence": 0.0-1.0
}}

**Severity Guidelines for Deprecations**:
- 0-2: Future deprecations, no immediate action needed
- 3-4: Deprecated but functional, plan migration
- 5-6: Deprecated with near-term removal, migrate soon
- 7-8: Will break in target version, must migrate before upgrade
- 9-10: Critical APIs breaking, major application changes required

Provide specific kubectl commands or manifest changes where possible.
"""

    CLUSTER_READINESS_ASSESSMENT = """
You are a site reliability engineer assessing cluster readiness for an EKS upgrade.

**Cluster Information**:
{cluster_info}

**Health Metrics**:
{health_metrics}

**Resource Utilization**:
{resource_utilization}

**Task**: Assess whether the cluster is in a suitable state for a major upgrade operation.

**Assessment Areas**:
1. **Resource Capacity**: Sufficient resources for Blue/Green deployment?
2. **Health Status**: Are all critical components healthy?
3. **Workload Stability**: Are applications running stably?
4. **Timing**: Is this a good time for maintenance?
5. **Dependencies**: Are external dependencies ready?

**Output Format** (respond with valid JSON):
{{
    "findings": [
        "Overall cluster readiness assessment"
    ],
    "breaking_changes": [
        "Critical issues that prevent upgrade"
    ],
    "deprecations": [
        "Warnings about cluster state or timing"
    ],
    "recommendations": [
        "Actions to improve readiness or optimal timing"
    ],
    "severity_score": 0.0-10.0,
    "confidence": 0.0-1.0
}}

**Readiness Score Guidelines**:
- 0-2: Excellent - Ideal conditions for upgrade
- 3-4: Good - Minor optimizations recommended
- 5-6: Fair - Some preparation needed
- 7-8: Poor - Significant issues to address first
- 9-10: Critical - Unsafe to proceed with upgrade

Consider factors like resource availability, recent incidents, planned maintenance windows, and business impact.
"""

    ROLLBACK_DECISION = """
You are an incident response engineer deciding whether to trigger an emergency rollback during an EKS upgrade.

**Upgrade Status**:
{upgrade_status}

**Current Metrics**:
{current_metrics}

**Error Indicators**:
{error_indicators}

**Traffic Distribution**:
{traffic_distribution}

**Task**: Determine if an immediate rollback is necessary based on the current situation.

**Decision Factors**:
1. **Service Availability**: Is the service still available to users?
2. **Error Rates**: Are error rates within acceptable thresholds?
3. **Performance**: Is performance degraded beyond SLA limits?
4. **Data Integrity**: Is there any risk to data consistency?
5. **Recovery Time**: Can issues be resolved faster than rollback?

**Output Format** (respond with valid JSON):
{{
    "findings": [
        "Critical assessment of current upgrade status"
    ],
    "breaking_changes": [
        "Immediate threats requiring rollback"
    ],
    "deprecations": [
        "Warning signs that suggest caution"
    ],
    "recommendations": [
        "Immediate actions: ROLLBACK, CONTINUE, or INVESTIGATE"
    ],
    "severity_score": 0.0-10.0,
    "confidence": 0.0-1.0
}}

**Rollback Decision Guidelines**:
- 0-3: CONTINUE - Metrics within normal ranges
- 4-5: MONITOR - Watch closely, prepare for rollback
- 6-7: INVESTIGATE - Pause traffic increase, diagnose issues
- 8-9: ROLLBACK - Significant service degradation
- 10: EMERGENCY ROLLBACK - Critical service failure

Time is critical - err on the side of service availability and user experience.
"""