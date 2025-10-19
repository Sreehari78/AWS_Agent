# Task 3.1: Amazon Bedrock Integration Implementation

## Overview

This document details the complete implementation of Amazon Bedrock integration for the EKS Upgrade Agent, including the modular architecture, components, testing strategy, and usage examples.

## Requirements Addressed

- **Requirement 2.2**: AI-powered analysis capabilities using Amazon Bedrock
- **Requirement 2.5**: Cost optimization and rate limiting mechanisms

## Architecture Overview

The Bedrock integration follows a modular architecture with clear separation of concerns:

```
src/eks_upgrade_agent/common/aws_ai/
├── __init__.py              # Module exports
├── bedrock_client.py        # Main client interface
├── rate_limiter.py          # Rate limiting functionality
├── cost_tracker.py          # Cost tracking and thresholds
├── model_invoker.py         # Low-level model invocation
└── prompt_templates.py      # Prompt templates for analysis
```

## Implementation Details

### 1. BedrockClient (bedrock_client.py)

**Purpose**: Main interface for Bedrock operations with high-level analysis methods.

**Key Features**:

- Orchestrates rate limiting, cost tracking, and model invocation
- Provides specialized analysis methods for different use cases
- Handles response parsing and result formatting
- Integrates with existing logging and error handling

**Key Methods**:

- `analyze_text()`: Generic text analysis with customizable prompts
- `analyze_release_notes()`: Specialized release notes analysis
- `make_upgrade_decision()`: Decision-making based on analysis results
- `get_cost_summary()`: Cost and usage statistics

### 2. RateLimiter (rate_limiter.py)

**Purpose**: Implements sliding window rate limiting to prevent API quota exhaustion.

**Key Features**:

- Configurable requests per minute limit
- Sliding window approach with automatic cleanup
- Thread-safe request tracking
- Detailed logging for monitoring

**Implementation Details**:

- Uses timestamp-based request tracking
- Automatically removes requests older than 1 minute
- Raises `BedrockRateLimitError` when limits exceeded
- Provides current usage statistics

### 3. CostTracker (cost_tracker.py)

**Purpose**: Tracks daily costs and enforces spending thresholds.

**Key Features**:

- Automatic daily cost reset at midnight UTC
- Claude 3 Sonnet pricing calculations
- Configurable daily spending thresholds
- Token usage to cost conversion

**Cost Calculation**:

```python
# Claude 3 Sonnet pricing (2024)
input_cost = (input_tokens / 1000) * 0.003   # $0.003 per 1K tokens
output_cost = (output_tokens / 1000) * 0.015 # $0.015 per 1K tokens
total_cost = input_cost + output_cost
```

### 4. ModelInvoker (model_invoker.py)

**Purpose**: Low-level Bedrock model invocation with retry logic and error handling.

**Key Features**:

- Exponential backoff retry strategy (3 attempts)
- Comprehensive error handling for AWS service errors
- Integration with rate limiter and cost tracker
- Structured logging for debugging

**Retry Configuration**:

- Stop after 3 attempts
- Exponential backoff: 4-10 seconds
- Retries on `ClientError` and `BotoCoreError`
- Detailed error logging

### 5. PromptTemplates (prompt_templates.py)

**Purpose**: Centralized prompt templates for different analysis scenarios.

**Templates Included**:

- `RELEASE_NOTES_ANALYSIS`: Analyzes release notes for breaking changes
- `UPGRADE_DECISION`: Makes upgrade go/no-go decisions
- `DEPRECATION_IMPACT_ANALYSIS`: Analyzes deprecated API impact
- `CLUSTER_READINESS_ASSESSMENT`: Assesses cluster readiness
- `ROLLBACK_DECISION`: Emergency rollback decision making

**Template Features**:

- Structured JSON output format
- Severity scoring (0-10 scale)
- Confidence scoring (0-1 scale)
- Specific guidance for each use case

## Modularization Benefits

### Before Modularization Issues:

- Single 400+ line file with mixed responsibilities
- Difficult to test individual components
- Hard to maintain and extend
- Tight coupling between concerns

### After Modularization Benefits:

- **Single Responsibility**: Each module has one clear purpose
- **Testability**: Individual components can be tested in isolation
- **Maintainability**: Changes to one component don't affect others
- **Extensibility**: Easy to add new features or replace components
- **Reusability**: Components can be used independently

## Testing Strategy

### Test Structure

```
tests/unit/
├── test_bedrock_client.py    # Main client integration tests
├── test_rate_limiter.py      # Rate limiting functionality
├── test_cost_tracker.py      # Cost tracking and thresholds
└── test_model_invoker.py     # Model invocation and retry logic
```

### Test Coverage (31 tests total)

- **BedrockClient**: 7 tests covering initialization, analysis, and integration
- **RateLimiter**: 7 tests covering limits, cleanup, and usage tracking
- **CostTracker**: 9 tests covering estimation, thresholds, and resets
- **ModelInvoker**: 8 tests covering invocation, errors, and retries

### Testing Approach

- **Mocking Strategy**: Mock AWS services and external dependencies
- **Unit Testing**: Test individual components in isolation
- **Integration Testing**: Test component interactions
- **Error Scenarios**: Test failure modes and error handling

## Configuration

### AWS AI Configuration (AWSAIConfig)

```python
config = AWSAIConfig(
    # Bedrock settings
    bedrock_model_id="anthropic.claude-3-sonnet-20240229-v1:0",
    bedrock_region="us-east-1",
    bedrock_max_tokens=4096,
    bedrock_temperature=0.1,

    # Rate limiting
    max_bedrock_requests_per_minute=60,

    # Cost control
    cost_threshold_usd=100.0,

    # AWS credentials (optional)
    aws_profile="my-profile",
    aws_access_key_id="...",
    aws_secret_access_key="...",
)
```

## Usage Examples

### Basic Text Analysis

```python
from src.eks_upgrade_agent.common.aws_ai import BedrockClient
from src.eks_upgrade_agent.common.models.aws_ai import AWSAIConfig

# Initialize client
config = AWSAIConfig()
client = BedrockClient(config)

# Analyze text
result = client.analyze_text(
    text="Kubernetes v1.28 removes dockershim support",
    prompt_template="Analyze this for breaking changes: {text}"
)

print(f"Severity: {result.severity_score}/10")
print(f"Breaking changes: {result.breaking_changes}")
```

### Release Notes Analysis

```python
# Analyze release notes
result = client.analyze_release_notes(
    release_notes=release_notes_text,
    source_version="1.27",
    target_version="1.28"
)

# Check results
if result.severity_score > 7:
    print("High risk upgrade - review breaking changes")
    for change in result.breaking_changes:
        print(f"- {change}")
```

### Upgrade Decision Making

```python
# Make upgrade decision
decision = client.make_upgrade_decision(
    cluster_state=cluster_info,
    analysis_results=[release_analysis, deprecation_analysis],
    target_version="1.28"
)

# Act on decision
if decision.severity_score <= 3:
    print("✅ PROCEED - Low risk upgrade")
elif decision.severity_score <= 6:
    print("⚠️ PROCEED WITH CAUTION")
else:
    print("🛑 HALT - High risk, preparation needed")
```

## Error Handling

### Custom Exceptions

- `BedrockRateLimitError`: Rate limit exceeded
- `BedrockCostThresholdError`: Cost threshold exceeded
- `AWSServiceError`: General AWS service errors

### Error Scenarios Handled

- Network connectivity issues
- AWS service throttling
- Invalid model responses
- Authentication failures
- Cost threshold breaches
- Rate limit violations

## Monitoring and Observability

### Structured Logging

All components use structured logging with contextual information:

```python
logger.info(
    "Text analysis completed",
    analysis_id=result.analysis_id,
    processing_time=processing_time,
    findings_count=len(result.findings),
    severity_score=result.severity_score,
)
```

### Cost and Usage Tracking

```python
# Get usage summary
summary = client.get_cost_summary()
print(f"Daily cost: ${summary['daily_cost_usd']:.4f}")
print(f"Requests (last minute): {summary['requests_last_minute']}")
```

## Integration Points

### Existing System Integration

- **Models**: Uses existing `AWSAIConfig` and `BedrockAnalysisResult`
- **Error Handling**: Integrates with existing `AWSServiceError` hierarchy
- **Logging**: Uses existing structured logging setup
- **Configuration**: Compatible with existing configuration system

### Dependencies

- `boto3[bedrock]>=1.34.0`: AWS SDK for Bedrock
- `tenacity>=8.2.3`: Retry logic
- `structlog>=23.2.0`: Structured logging
- `pydantic>=2.5.0`: Data validation

## Performance Considerations

### Rate Limiting

- Default: 60 requests/minute (configurable)
- Sliding window prevents burst usage
- Automatic cleanup of old request records

### Cost Optimization

- Real-time cost tracking
- Daily spending limits
- Token usage monitoring
- Automatic cost reset at midnight UTC

### Retry Strategy

- Exponential backoff prevents API hammering
- Maximum 3 retry attempts
- Intelligent error classification

## Security Considerations

### Credentials Management

- Supports AWS profiles, IAM roles, and explicit credentials
- No hardcoded credentials in code
- Follows AWS security best practices

### Data Handling

- No sensitive data logged
- Secure transmission to AWS services
- Proper error message sanitization

## Future Enhancements

### Potential Improvements

1. **Multi-Model Support**: Support for Claude 3 Haiku and other models
2. **Caching**: Response caching for repeated analyses
3. **Batch Processing**: Batch multiple requests for efficiency
4. **Advanced Metrics**: More detailed usage and performance metrics
5. **Custom Prompts**: User-defined prompt templates

### Extension Points

- New analysis types can be added via prompt templates
- Additional cost tracking metrics
- Custom rate limiting strategies
- Alternative retry policies

## Conclusion

The modular Bedrock integration provides a robust, scalable foundation for AI-powered EKS upgrade analysis. The clean architecture ensures maintainability while comprehensive testing guarantees reliability. The implementation successfully addresses all requirements while providing room for future enhancements.

## Files Created/Modified

### New Files

- `src/eks_upgrade_agent/common/aws_ai/bedrock_client.py`
- `src/eks_upgrade_agent/common/aws_ai/rate_limiter.py`
- `src/eks_upgrade_agent/common/aws_ai/cost_tracker.py`
- `src/eks_upgrade_agent/common/aws_ai/model_invoker.py`
- `src/eks_upgrade_agent/common/aws_ai/prompt_templates.py`
- `tests/unit/test_bedrock_client.py`
- `tests/unit/test_rate_limiter.py`
- `tests/unit/test_cost_tracker.py`
- `tests/unit/test_model_invoker.py`
- `examples/bedrock_integration_example.py`

### Modified Files

- `src/eks_upgrade_agent/common/aws_ai/__init__.py` (updated exports)

### Test Results

All 31 tests pass successfully, confirming the implementation meets requirements and handles edge cases properly.
