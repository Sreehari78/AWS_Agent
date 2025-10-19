# EKS Upgrade Agent

An autonomous AI system for managing Amazon EKS cluster upgrades with zero downtime using AWS AI services.

## Overview

The EKS Upgrade Agent is a sophisticated autonomous system that leverages AWS AI services including Amazon Bedrock, Amazon Comprehend, AWS Step Functions, and Amazon EventBridge to intelligently manage EKS cluster upgrades. The agent employs a Blue/Green deployment strategy to ensure zero downtime while providing advanced analysis and decision-making capabilities.

### Key Features

- **Zero Downtime Upgrades**: Blue/Green deployment strategy with gradual traffic shifting
- **AI-Powered Analysis**: Amazon Bedrock (Claude 3) for intelligent decision-making
- **Automated Detection**: Amazon Comprehend for release notes analysis and deprecation scanning
- **Multi-Version Jumps**: Support for upgrading across multiple EKS versions
- **GitOps Integration**: Seamless integration with ArgoCD and Flux
- **Infrastructure as Code**: Terraform and EKS Blueprints support
- **Comprehensive Validation**: Automated testing and health monitoring
- **Intelligent Rollback**: Automatic rollback on validation failures

### Architecture

The agent follows an agentic AI paradigm with four core modules:

1. **Perception Module**: Collects data from AWS APIs, Kubernetes clusters, and release notes
2. **Reasoning Module**: Analyzes data using AWS AI services and generates upgrade plans
3. **Execution Module**: Implements upgrade operations including infrastructure provisioning
4. **Validation Module**: Verifies upgrade success and triggers rollbacks when needed

## AWS AI Services Integration

### Amazon Bedrock

- **Model**: Claude 3 Sonnet/Haiku for advanced reasoning and analysis
- **Use Cases**: Release notes analysis, breaking change detection, upgrade planning
- **Configuration**: Requires Bedrock model access and appropriate IAM permissions

### Amazon Comprehend

- **Features**: Named Entity Recognition (NER) and custom classification
- **Use Cases**: Kubernetes terminology extraction, deprecation identification
- **Configuration**: Custom models for Kubernetes-specific terminology

### AWS Step Functions

- **Purpose**: Orchestrate upgrade workflows and manage state transitions
- **Benefits**: Visual workflow monitoring, error handling, and retry logic
- **Integration**: Coordinates between agent phases and external services

### Amazon EventBridge

- **Function**: Event-driven coordination and notifications
- **Use Cases**: Validation triggers, rollback coordination, status updates
- **Configuration**: Custom event buses for upgrade-specific events

## Prerequisites

### AWS Requirements

1. **AWS Account** with appropriate permissions
2. **Amazon Bedrock Access** to Claude 3 models
3. **Amazon Comprehend** service access
4. **AWS Step Functions** and **EventBridge** permissions
5. **EKS Cluster** access and management permissions
6. **Route 53** for traffic management (Blue/Green deployments)

### Local Requirements

- Python 3.9 or higher
- AWS CLI configured with appropriate credentials
- kubectl configured for target EKS clusters
- Terraform (for infrastructure provisioning)
- Helm (for application deployments)

### IAM Permissions

The agent requires the following AWS IAM permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream",
        "comprehend:DetectEntities",
        "comprehend:ClassifyDocument",
        "stepfunctions:StartExecution",
        "stepfunctions:DescribeExecution",
        "events:PutEvents",
        "eks:*",
        "route53:*",
        "ssm:GetParameter",
        "ssm:PutParameter"
      ],
      "Resource": "*"
    }
  ]
}
```

## Installation

### From PyPI (Recommended)

```bash
pip install eks-upgrade-agent
```

### From Source

```bash
git clone https://github.com/eks-upgrade-agent/eks-upgrade-agent.git
cd eks-upgrade-agent
pip install -e .
```

### Development Installation

```bash
git clone https://github.com/eks-upgrade-agent/eks-upgrade-agent.git
cd eks-upgrade-agent
pip install -e ".[dev]"
```

## Quick Start

### 1. Configure AWS AI Services

Create a configuration file `config.yaml`:

```yaml
aws_ai:
  bedrock:
    model_id: "anthropic.claude-3-sonnet-20240229-v1:0"
    region: "us-east-1"
  comprehend:
    region: "us-east-1"
  step_functions:
    state_machine_arn: "arn:aws:states:us-east-1:123456789012:stateMachine:EKSUpgradeAgent"
  eventbridge:
    bus_name: "eks-upgrade-events"

cluster:
  name: "my-eks-cluster"
  region: "us-east-1"

upgrade:
  strategy: "blue_green"
  traffic_shift_intervals: [10, 25, 50, 75, 100]
  validation_timeout: 300

logging:
  level: "INFO"
  format: "json"
```

### 2. Run an Upgrade

```bash
# Basic upgrade command
eks-upgrade-agent upgrade \
  --cluster-name my-eks-cluster \
  --target-version 1.29 \
  --strategy blue_green \
  --config config.yaml

# With additional options
eks-upgrade-agent upgrade \
  --cluster-name my-eks-cluster \
  --target-version 1.29 \
  --strategy blue_green \
  --config config.yaml \
  --dry-run \
  --verbose
```

### 3. Monitor Progress

The agent provides real-time progress updates and can be monitored through:

- CLI output with progress bars and status updates
- AWS Step Functions console for workflow visualization
- CloudWatch logs for detailed execution logs
- EventBridge events for integration with monitoring systems

## Configuration

### AWS AI Services Setup

#### Amazon Bedrock Configuration

1. **Enable Bedrock Access**: Request access to Claude 3 models in the AWS console
2. **Configure Model Access**: Ensure your IAM role has `bedrock:InvokeModel` permissions
3. **Set Region**: Bedrock is available in specific regions (us-east-1, us-west-2, etc.)

```yaml
aws_ai:
  bedrock:
    model_id: "anthropic.claude-3-sonnet-20240229-v1:0"
    region: "us-east-1"
    max_tokens: 4000
    temperature: 0.1
```

#### Amazon Comprehend Setup

1. **Create Custom Models** (Optional): Train custom NER models for Kubernetes terminology
2. **Configure Endpoints**: Set up real-time endpoints for high-throughput scenarios

```yaml
aws_ai:
  comprehend:
    region: "us-east-1"
    custom_model_arn: "arn:aws:comprehend:us-east-1:123456789012:entity-recognizer/k8s-terminology"
```

#### AWS Step Functions Configuration

1. **Create State Machine**: Deploy the provided Step Functions definition
2. **Configure IAM Roles**: Ensure proper permissions for EKS and other AWS services

```yaml
aws_ai:
  step_functions:
    state_machine_arn: "arn:aws:states:us-east-1:123456789012:stateMachine:EKSUpgradeAgent"
    execution_role_arn: "arn:aws:iam::123456789012:role/EKSUpgradeAgentExecutionRole"
```

### Advanced Configuration

#### Blue/Green Strategy Configuration

```yaml
upgrade:
  strategy: "blue_green"
  blue_green:
    traffic_shift_intervals: [10, 25, 50, 75, 100] # Percentage increments
    validation_wait_time: 300 # Seconds between shifts
    health_check_timeout: 180 # Seconds for health validation
    rollback_on_failure: true
    preserve_blue_cluster: false # Keep blue cluster after successful upgrade
```

#### Validation Configuration

```yaml
validation:
  health_checks:
    enabled: true
    timeout: 300
    retry_attempts: 3

  metrics_analysis:
    enabled: true
    sla_thresholds:
      error_rate: 0.01 # 1% error rate threshold
      latency_p99: 1000 # 1 second P99 latency threshold

  test_suites:
    enabled: true
    test_timeout: 600
    parallel_execution: true
```

## Usage Examples

### Basic Upgrade

```python
from eks_upgrade_agent import EKSUpgradeAgent
from eks_upgrade_agent.common import AgentConfig

# Load configuration
config = AgentConfig.from_file("config.yaml")

# Initialize agent
agent = EKSUpgradeAgent(config)

# Run upgrade
result = await agent.run_upgrade(
    cluster_name="my-eks-cluster",
    target_version="1.29",
    strategy="blue_green"
)

print(f"Upgrade completed: {result.success}")
```

### Custom Strategy Implementation

```python
from eks_upgrade_agent.reasoning.strategies import UpgradeStrategy

class CustomUpgradeStrategy(UpgradeStrategy):
    def generate_plan(self, cluster_state, target_version):
        # Custom upgrade logic
        pass

# Register custom strategy
agent.register_strategy("custom", CustomUpgradeStrategy)
```

### Monitoring and Callbacks

```python
def progress_callback(step, progress):
    print(f"Step {step}: {progress}% complete")

def validation_callback(result):
    if not result.success:
        print(f"Validation failed: {result.errors}")

agent.set_progress_callback(progress_callback)
agent.set_validation_callback(validation_callback)
```

## Troubleshooting

### Common Issues

#### AWS AI Services Access

**Issue**: `AccessDeniedException` when calling Bedrock or Comprehend

**Solution**:

1. Verify IAM permissions include required AI service actions
2. Check service availability in your AWS region
3. Ensure Bedrock model access has been requested and approved

#### EKS Cluster Access

**Issue**: `Unauthorized` errors when accessing EKS cluster

**Solution**:

1. Verify kubectl configuration and context
2. Check EKS cluster IAM roles and RBAC permissions
3. Ensure AWS credentials have EKS access permissions

#### Traffic Shifting Failures

**Issue**: Route 53 weighted routing not updating

**Solution**:

1. Verify Route 53 hosted zone permissions
2. Check DNS propagation delays
3. Ensure health checks are properly configured

### Debug Mode

Enable debug logging for detailed troubleshooting:

```bash
eks-upgrade-agent upgrade \
  --cluster-name my-eks-cluster \
  --target-version 1.29 \
  --strategy blue_green \
  --config config.yaml \
  --log-level DEBUG
```

### Log Analysis

The agent generates structured JSON logs that can be analyzed with tools like:

- AWS CloudWatch Insights
- Elasticsearch/Kibana
- Splunk
- Local log analysis tools

## Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Development Setup

```bash
git clone https://github.com/eks-upgrade-agent/eks-upgrade-agent.git
cd eks-upgrade-agent
pip install -e ".[dev]"
pre-commit install
```

### Running Tests

```bash
# Unit tests
pytest tests/unit/

# Integration tests (requires AWS credentials)
pytest tests/integration/

# All tests with coverage
pytest --cov=eks_upgrade_agent tests/
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- **Documentation**: [https://eks-upgrade-agent.readthedocs.io/](https://eks-upgrade-agent.readthedocs.io/)
- **Issues**: [GitHub Issues](https://github.com/eks-upgrade-agent/eks-upgrade-agent/issues)
- **Discussions**: [GitHub Discussions](https://github.com/eks-upgrade-agent/eks-upgrade-agent/discussions)
- **Email**: support@eks-upgrade-agent.com

## Roadmap

- [ ] Support for additional upgrade strategies (rolling, canary)
- [ ] Integration with more GitOps tools (Tekton, Jenkins X)
- [ ] Enhanced AI analysis with additional AWS AI services
- [ ] Multi-cloud support (Azure AKS, Google GKE)
- [ ] Advanced cost optimization features
- [ ] Compliance and security scanning integration

## Acknowledgments

- AWS AI Services team for Bedrock and Comprehend capabilities
- Kubernetes community for excellent tooling and documentation
- EKS team for comprehensive upgrade guidance and best practices
