# Task 2.3 Implementation: Centralized Logging and Exception Handling

## Overview

Task 2.3 implemented a comprehensive centralized logging and exception handling system for the EKS Upgrade Agent. This system provides structured logging with JSON output, AWS CloudWatch integration, and a hierarchical exception system with proper error context preservation.

## What Was Implemented

### 1. Custom Exception Hierarchy (`src/eks_upgrade_agent/common/exceptions.py`)

#### Base Exception Class: `EKSUpgradeAgentError`

- **Purpose**: Foundation for all EKS Upgrade Agent errors
- **Key Features**:
  - Error context preservation with `context` dictionary
  - Structured error data via `to_dict()` method
  - Exception chaining with `cause` parameter
  - Recoverable/non-recoverable error classification
  - Timestamp tracking with timezone-aware datetime
  - Stack trace preservation
  - Method chaining with `add_context()`

#### Specialized Exception Classes

1. **`PerceptionError`**

   - **Use Case**: Data collection and perception phase failures
   - **Examples**: AWS API failures, Kubernetes API timeouts, release notes collection errors
   - **Special Context**: `source`, `api_error_type`, `api_error_message`

2. **`PlanningError`**

   - **Use Case**: Upgrade planning and reasoning phase failures
   - **Examples**: NLP analysis failures, strategy selection errors, plan generation issues
   - **Special Context**: `planning_phase`, `invalid_config`

3. **`ExecutionError`**

   - **Use Case**: Upgrade execution phase failures
   - **Examples**: Infrastructure provisioning failures, GitOps deployment errors, CLI command failures
   - **Special Context**: `execution_step`, `command`, `exit_code`, `stdout`, `stderr`

4. **`ValidationError`**

   - **Use Case**: Validation phase failures
   - **Examples**: Health check failures, metrics analysis problems, test execution errors
   - **Special Context**: `validation_type`, `failed_checks`, `metrics`, `threshold_violations`

5. **`ConfigurationError`**

   - **Use Case**: Configuration validation and loading issues
   - **Examples**: Invalid YAML files, missing required settings, AWS credential issues
   - **Special Context**: `config_file`, `missing_keys`, `invalid_values`

6. **`AWSServiceError`**

   - **Use Case**: AWS service integration failures
   - **Examples**: Bedrock API errors, Comprehend service issues, Step Functions failures
   - **Special Context**: `service_name`, `operation`, `aws_error_code`, `aws_error_message`

7. **`RollbackError`**
   - **Use Case**: Rollback operation failures (critical errors)
   - **Examples**: Failed rollback attempts requiring manual intervention
   - **Special Context**: `rollback_step`, `original_error_type`, `original_error_message`
   - **Note**: Always marked as non-recoverable

#### Convenience Functions

- `create_perception_error()` - Quick PerceptionError creation
- `create_execution_error()` - Quick ExecutionError creation
- `create_validation_error()` - Quick ValidationError creation

### 2. Structured Logging System (`src/eks_upgrade_agent/common/logger.py`)

#### Core Components

1. **`LoggerConfig` Class**

   - Centralized configuration for all logging settings
   - Configurable log levels, formats, and output destinations
   - Support for console, file, and CloudWatch outputs

2. **`CloudWatchHandler` Class**
   - Custom logging handler for AWS CloudWatch Logs integration
   - Automatic log group and stream creation
   - Graceful fallback to local logging when CloudWatch is unavailable
   - Proper AWS credential handling and error recovery

#### Structured Logging Features

1. **JSON Output Format**

   - Uses `structlog` for structured logging
   - Consistent JSON format for all log messages
   - Machine-readable log data for analysis

2. **Custom Processors**

   - `add_context_processor()`: Adds common context (timestamp, log level, process ID, thread name)
   - `add_exception_processor()`: Handles exception logging with structured data

3. **Logging Utilities**
   - `log_exception()`: Structured exception logging with context
   - `log_upgrade_step()`: Consistent upgrade progress tracking
   - `log_aws_api_call()`: AWS API call success/failure tracking

#### Configuration Options

- **Log Levels**: DEBUG, INFO, WARNING, ERROR, CRITICAL
- **Output Formats**: JSON (structured) or Console (human-readable)
- **Output Destinations**: Console, rotating log files, AWS CloudWatch
- **CloudWatch Integration**: Automatic log group/stream management

### 3. Integration and Exports (`src/eks_upgrade_agent/common/__init__.py`)

Updated the common module to export all new logging and exception components:

#### Exception Exports

- All exception classes and convenience functions
- Easy import: `from eks_upgrade_agent.common import PerceptionError`

#### Logging Exports

- Logger configuration and setup functions
- Utility functions for structured logging
- Easy import: `from eks_upgrade_agent.common import get_logger, log_exception`

### 4. Comprehensive Unit Tests

#### Exception Tests (`tests/unit/test_exceptions.py`)

- **16 test methods** covering all exception classes
- Tests for error context preservation, exception chaining, and structured data
- Validation of convenience functions and method chaining

#### Logging Tests (`tests/unit/test_logger.py`)

- **21 test methods** covering all logging functionality
- CloudWatch handler testing with mock AWS services
- Processor testing for context and exception handling
- Configuration testing for various output scenarios

## Technical Implementation Details

### Error Context Preservation

```python
# Example of rich error context
error = ExecutionError(
    "Terraform deployment failed",
    execution_step="provision_cluster",
    command="terraform apply -auto-approve",
    exit_code=1,
    stderr="Error: Invalid AWS credentials"
)

# Structured error data
error_data = error.to_dict()
# Contains: error_type, error_code, message, context, timestamp, stack_trace, etc.
```

### Structured Logging Example

```python
from eks_upgrade_agent.common import get_logger, log_upgrade_step

logger = get_logger()

# Structured upgrade progress logging
log_upgrade_step(
    logger,
    step_name="Deploy Applications",
    step_id="step_123",
    status="started",
    cluster_name="prod-cluster",
    namespace="default"
)
```

### CloudWatch Integration

```python
from eks_upgrade_agent.common import LoggerConfig, setup_logging

# Configure CloudWatch logging
config = LoggerConfig(
    log_level="INFO",
    log_format="json",
    cloudwatch_log_group="/aws/eks-upgrade-agent",
    cloudwatch_region="us-east-1",
    enable_cloudwatch=True
)

logger = setup_logging(config)
```

## Requirements Satisfied

### Requirement 5.5: Error Handling and Logging

- ✅ Comprehensive exception hierarchy for all failure scenarios
- ✅ Structured error context preservation
- ✅ Proper exception chaining and cause tracking
- ✅ Recoverable vs non-recoverable error classification

### Requirement 6.4: Monitoring and Observability

- ✅ Structured JSON logging for machine analysis
- ✅ AWS CloudWatch integration for centralized log management
- ✅ Consistent logging patterns for upgrade progress tracking
- ✅ AWS API call monitoring and error tracking

## Files Created/Modified

### New Files

1. `src/eks_upgrade_agent/common/exceptions.py` - Exception hierarchy (400+ lines)
2. `src/eks_upgrade_agent/common/logger.py` - Logging system (500+ lines)
3. `tests/unit/test_exceptions.py` - Exception tests (300+ lines)
4. `tests/unit/test_logger.py` - Logging tests (400+ lines)

### Modified Files

1. `src/eks_upgrade_agent/common/__init__.py` - Added exports for new components

## Key Benefits

1. **Consistent Error Handling**: All errors follow the same structured pattern
2. **Rich Context**: Errors preserve detailed context for debugging
3. **Structured Logging**: Machine-readable logs for analysis and monitoring
4. **AWS Integration**: Native CloudWatch support for production environments
5. **Comprehensive Testing**: 37 unit tests ensure reliability
6. **Developer Experience**: Easy-to-use APIs and convenience functions

## Usage Examples

### Exception Handling

```python
try:
    # Some operation that might fail
    deploy_application()
except Exception as e:
    # Create structured error with context
    error = create_execution_error(
        "Application deployment failed",
        step="deploy_apps",
        namespace="production",
        original_error=e
    )
    log_exception(logger, error)
    raise error
```

### Structured Logging

```python
# Initialize logging
logger = get_logger("my_module")

# Log upgrade progress
log_upgrade_step(logger, "Provision Cluster", "step_1", "started")

# Log AWS API calls
log_aws_api_call(logger, "bedrock", "invoke_model", True, duration_ms=150)

# Log with custom context
logger.info("Processing cluster", cluster_name="prod", node_count=5)
```

This implementation provides a solid foundation for error handling and logging throughout the EKS Upgrade Agent, ensuring consistent error reporting, structured logging, and proper integration with AWS monitoring services.
