# Configuration Examples

This directory contains sample configuration files for the EKS Upgrade Agent.

## ⚠️ Security Notice

**NEVER commit real credentials, API keys, or sensitive information to version control!**

## Files

- `sample_config.yaml` - Comprehensive example showing all configuration options with placeholder values

## Usage

1. Copy the sample configuration file:

   ```bash
   cp examples/config/sample_config.yaml config.yaml
   ```

2. Replace all placeholder values with your actual values:

   - `YOUR_ACCOUNT_ID` - Your AWS account ID
   - `YOUR_KMS_KEY_ID` - Your KMS key ID for encryption
   - `YOUR_TERRAFORM_STATE_BUCKET` - Your Terraform state S3 bucket
   - `YOUR_ARTIFACTS_BUCKET` - Your artifacts storage S3 bucket
   - `YOUR_SLACK_WEBHOOK_URL` - Your Slack webhook URL
   - Email addresses and other organization-specific values

3. Store sensitive values securely:
   - Use AWS Systems Manager Parameter Store for production secrets
   - Use environment variables for local development
   - Consider using AWS Secrets Manager for highly sensitive data

## Configuration Methods

The EKS Upgrade Agent supports multiple configuration methods (in priority order):

1. **Direct instantiation** (highest priority)
2. **Environment variables** (with `EKS_UPGRADE_AGENT_` prefix)
3. **YAML configuration files**
4. **AWS Systems Manager Parameter Store**
5. **Default values** (lowest priority)

## Environment Variables

All configuration options can be overridden using environment variables with the `EKS_UPGRADE_AGENT_` prefix:

```bash
export EKS_UPGRADE_AGENT_DEBUG=true
export EKS_UPGRADE_AGENT_AWS_AI__BEDROCK_REGION=us-west-2
export EKS_UPGRADE_AGENT_LOGGING__LEVEL=DEBUG
```

## AWS Systems Manager Integration

For production deployments, store sensitive configuration in AWS Systems Manager Parameter Store:

```bash
# Store configuration parameters
aws ssm put-parameter \
  --name "/eks-upgrade-agent/prod/aws_ai/bedrock_model_id" \
  --value "anthropic.claude-3-sonnet-20240229-v1:0" \
  --type "String"

aws ssm put-parameter \
  --name "/eks-upgrade-agent/prod/notifications/slack_webhook_url" \
  --value "https://hooks.slack.com/services/..." \
  --type "SecureString"
```

Then load configuration from SSM:

```python
from eks_upgrade_agent.common import AgentConfig

config = AgentConfig.from_ssm("/eks-upgrade-agent/prod/")
```

## Best Practices

1. **Use different configurations for different environments** (dev, staging, prod)
2. **Store secrets in AWS Systems Manager Parameter Store or Secrets Manager**
3. **Use IAM roles instead of access keys when possible**
4. **Enable credential rotation for long-lived credentials**
5. **Use KMS encryption for sensitive parameters**
6. **Regularly audit and rotate credentials**
7. **Use least-privilege IAM policies**

## Validation

The configuration system includes comprehensive validation:

- Type checking and conversion
- Required field validation
- Cross-component dependency validation
- AWS credential validation
- Configuration consistency checks

Invalid configurations will raise descriptive error messages to help with troubleshooting.
