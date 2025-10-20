"""
AWS Step Functions integration for EKS upgrade state management.

This module provides a client for managing Step Functions state machines
that orchestrate the upgrade workflow phases.
"""

import json
import time
from datetime import datetime, UTC
from typing import Any, Dict, List, Optional, Union
from uuid import uuid4

import boto3
from botocore.exceptions import ClientError, BotoCoreError
from pydantic import BaseModel, Field, field_validator

from ...logging import get_logger
from ...handler import AWSServiceError, ExecutionError

logger = get_logger(__name__)


class StateMachineDefinition(BaseModel):
    """Step Functions state machine definition for upgrade workflows."""
    
    name: str = Field(..., description="State machine name")
    definition: Dict[str, Any] = Field(..., description="State machine definition")
    role_arn: str = Field(..., description="IAM role ARN for execution")
    timeout_seconds: int = Field(default=3600, description="Execution timeout")
    tags: Dict[str, str] = Field(default_factory=dict, description="Resource tags")
    
    @field_validator("timeout_seconds")
    @classmethod
    def validate_timeout(cls, v):
        if not 60 <= v <= 86400:  # 1 minute to 24 hours
            raise ValueError("Timeout must be between 60 and 86400 seconds")
        return v


class ExecutionResult(BaseModel):
    """Result of a Step Functions execution."""
    
    execution_arn: str = Field(..., description="Execution ARN")
    status: str = Field(..., description="Execution status")
    start_date: datetime = Field(..., description="Execution start time")
    stop_date: Optional[datetime] = Field(None, description="Execution stop time")
    input_data: Dict[str, Any] = Field(default_factory=dict, description="Input data")
    output_data: Optional[Dict[str, Any]] = Field(None, description="Output data")
    error: Optional[str] = Field(None, description="Error message if failed")


class StepFunctionsClient:
    """
    Client for AWS Step Functions integration.
    
    Manages state machines for orchestrating EKS upgrade workflows
    with proper error handling and monitoring.
    """
    
    def __init__(
        self,
        region: str = "us-east-1",
        aws_profile: Optional[str] = None,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        aws_session_token: Optional[str] = None
    ):
        """
        Initialize Step Functions client.
        
        Args:
            region: AWS region
            aws_profile: AWS profile name
            aws_access_key_id: AWS access key ID
            aws_secret_access_key: AWS secret access key
            aws_session_token: AWS session token
        """
        self.region = region
        
        # Create boto3 session
        session_kwargs = {}
        if aws_profile:
            session_kwargs["profile_name"] = aws_profile
        else:
            if aws_access_key_id:
                session_kwargs["aws_access_key_id"] = aws_access_key_id
            if aws_secret_access_key:
                session_kwargs["aws_secret_access_key"] = aws_secret_access_key
            if aws_session_token:
                session_kwargs["aws_session_token"] = aws_session_token
        
        self.session = boto3.Session(**session_kwargs)
        self.client = self.session.client("stepfunctions", region_name=region)
        
        logger.info(f"Initialized Step Functions client for region: {region}")
    
    def create_state_machine(self, definition: StateMachineDefinition) -> str:
        """
        Create a new Step Functions state machine.
        
        Args:
            definition: State machine definition
            
        Returns:
            State machine ARN
            
        Raises:
            AWSServiceError: If state machine creation fails
        """
        try:
            logger.info(f"Creating state machine: {definition.name}")
            
            response = self.client.create_state_machine(
                name=definition.name,
                definition=json.dumps(definition.definition),
                roleArn=definition.role_arn,
                type="STANDARD",
                tags=[{"key": k, "value": v} for k, v in definition.tags.items()]
            )
            
            state_machine_arn = response["stateMachineArn"]
            logger.info(f"Created state machine: {state_machine_arn}")
            
            return state_machine_arn
            
        except (ClientError, BotoCoreError) as e:
            error_msg = f"Failed to create state machine {definition.name}: {e}"
            logger.error(error_msg)
            raise AWSServiceError(error_msg) from e
    
    def update_state_machine(self, state_machine_arn: str, definition: StateMachineDefinition) -> None:
        """
        Update an existing Step Functions state machine.
        
        Args:
            state_machine_arn: State machine ARN
            definition: Updated state machine definition
            
        Raises:
            AWSServiceError: If state machine update fails
        """
        try:
            logger.info(f"Updating state machine: {state_machine_arn}")
            
            self.client.update_state_machine(
                stateMachineArn=state_machine_arn,
                definition=json.dumps(definition.definition),
                roleArn=definition.role_arn
            )
            
            logger.info(f"Updated state machine: {state_machine_arn}")
            
        except (ClientError, BotoCoreError) as e:
            error_msg = f"Failed to update state machine {state_machine_arn}: {e}"
            logger.error(error_msg)
            raise AWSServiceError(error_msg) from e
    
    def start_execution(
        self,
        state_machine_arn: str,
        input_data: Dict[str, Any],
        execution_name: Optional[str] = None
    ) -> str:
        """
        Start a Step Functions execution.
        
        Args:
            state_machine_arn: State machine ARN
            input_data: Input data for the execution
            execution_name: Optional execution name (auto-generated if None)
            
        Returns:
            Execution ARN
            
        Raises:
            AWSServiceError: If execution start fails
        """
        try:
            if execution_name is None:
                execution_name = f"upgrade-{int(time.time())}-{str(uuid4())[:8]}"
            
            logger.info(f"Starting execution: {execution_name}")
            
            response = self.client.start_execution(
                stateMachineArn=state_machine_arn,
                name=execution_name,
                input=json.dumps(input_data)
            )
            
            execution_arn = response["executionArn"]
            logger.info(f"Started execution: {execution_arn}")
            
            return execution_arn
            
        except (ClientError, BotoCoreError) as e:
            error_msg = f"Failed to start execution {execution_name}: {e}"
            logger.error(error_msg)
            raise AWSServiceError(error_msg) from e
    
    def stop_execution(self, execution_arn: str, error: str = "Manual stop", cause: str = "Stopped by user") -> None:
        """
        Stop a running Step Functions execution.
        
        Args:
            execution_arn: Execution ARN
            error: Error message
            cause: Cause of the stop
            
        Raises:
            AWSServiceError: If execution stop fails
        """
        try:
            logger.info(f"Stopping execution: {execution_arn}")
            
            self.client.stop_execution(
                executionArn=execution_arn,
                error=error,
                cause=cause
            )
            
            logger.info(f"Stopped execution: {execution_arn}")
            
        except (ClientError, BotoCoreError) as e:
            error_msg = f"Failed to stop execution {execution_arn}: {e}"
            logger.error(error_msg)
            raise AWSServiceError(error_msg) from e
    
    def get_execution_status(self, execution_arn: str) -> ExecutionResult:
        """
        Get the status of a Step Functions execution.
        
        Args:
            execution_arn: Execution ARN
            
        Returns:
            Execution result with status and details
            
        Raises:
            AWSServiceError: If status retrieval fails
        """
        try:
            logger.debug(f"Getting execution status: {execution_arn}")
            
            response = self.client.describe_execution(executionArn=execution_arn)
            
            # Parse output data if available
            output_data = None
            if "output" in response:
                try:
                    output_data = json.loads(response["output"])
                except json.JSONDecodeError:
                    output_data = {"raw_output": response["output"]}
            
            # Parse input data
            input_data = {}
            if "input" in response:
                try:
                    input_data = json.loads(response["input"])
                except json.JSONDecodeError:
                    input_data = {"raw_input": response["input"]}
            
            result = ExecutionResult(
                execution_arn=execution_arn,
                status=response["status"],
                start_date=response["startDate"].replace(tzinfo=UTC),
                stop_date=response.get("stopDate", {}).replace(tzinfo=UTC) if response.get("stopDate") else None,
                input_data=input_data,
                output_data=output_data,
                error=response.get("error")
            )
            
            return result
            
        except (ClientError, BotoCoreError) as e:
            error_msg = f"Failed to get execution status {execution_arn}: {e}"
            logger.error(error_msg)
            raise AWSServiceError(error_msg) from e
    
    def wait_for_execution(
        self,
        execution_arn: str,
        max_wait_seconds: int = 3600,
        poll_interval: int = 10
    ) -> ExecutionResult:
        """
        Wait for a Step Functions execution to complete.
        
        Args:
            execution_arn: Execution ARN
            max_wait_seconds: Maximum time to wait
            poll_interval: Polling interval in seconds
            
        Returns:
            Final execution result
            
        Raises:
            ExecutionError: If execution fails or times out
        """
        start_time = time.time()
        
        while time.time() - start_time < max_wait_seconds:
            result = self.get_execution_status(execution_arn)
            
            if result.status in ["SUCCEEDED", "FAILED", "TIMED_OUT", "ABORTED"]:
                if result.status == "SUCCEEDED":
                    logger.info(f"Execution completed successfully: {execution_arn}")
                else:
                    logger.error(f"Execution failed with status {result.status}: {execution_arn}")
                    if result.error:
                        logger.error(f"Error: {result.error}")
                
                return result
            
            logger.debug(f"Execution {execution_arn} status: {result.status}, waiting...")
            time.sleep(poll_interval)
        
        # Timeout reached
        error_msg = f"Execution {execution_arn} timed out after {max_wait_seconds} seconds"
        logger.error(error_msg)
        raise ExecutionError(error_msg)
    
    def list_executions(
        self,
        state_machine_arn: str,
        status_filter: Optional[str] = None,
        max_results: int = 100
    ) -> List[ExecutionResult]:
        """
        List executions for a state machine.
        
        Args:
            state_machine_arn: State machine ARN
            status_filter: Optional status filter (RUNNING, SUCCEEDED, FAILED, etc.)
            max_results: Maximum number of results
            
        Returns:
            List of execution results
            
        Raises:
            AWSServiceError: If listing fails
        """
        try:
            logger.debug(f"Listing executions for state machine: {state_machine_arn}")
            
            kwargs = {
                "stateMachineArn": state_machine_arn,
                "maxResults": max_results
            }
            
            if status_filter:
                kwargs["statusFilter"] = status_filter
            
            response = self.client.list_executions(**kwargs)
            
            executions = []
            for execution in response.get("executions", []):
                result = ExecutionResult(
                    execution_arn=execution["executionArn"],
                    status=execution["status"],
                    start_date=execution["startDate"].replace(tzinfo=UTC),
                    stop_date=execution.get("stopDate", {}).replace(tzinfo=UTC) if execution.get("stopDate") else None,
                    input_data={},  # Not included in list response
                    output_data=None
                )
                executions.append(result)
            
            return executions
            
        except (ClientError, BotoCoreError) as e:
            error_msg = f"Failed to list executions for {state_machine_arn}: {e}"
            logger.error(error_msg)
            raise AWSServiceError(error_msg) from e
    
    def delete_state_machine(self, state_machine_arn: str) -> None:
        """
        Delete a Step Functions state machine.
        
        Args:
            state_machine_arn: State machine ARN
            
        Raises:
            AWSServiceError: If deletion fails
        """
        try:
            logger.info(f"Deleting state machine: {state_machine_arn}")
            
            self.client.delete_state_machine(stateMachineArn=state_machine_arn)
            
            logger.info(f"Deleted state machine: {state_machine_arn}")
            
        except (ClientError, BotoCoreError) as e:
            error_msg = f"Failed to delete state machine {state_machine_arn}: {e}"
            logger.error(error_msg)
            raise AWSServiceError(error_msg) from e


def create_upgrade_state_machine_definition(
    cluster_name: str,
    target_version: str,
    strategy: str = "blue_green"
) -> Dict[str, Any]:
    """
    Create a standard upgrade state machine definition.
    
    Args:
        cluster_name: EKS cluster name
        target_version: Target Kubernetes version
        strategy: Upgrade strategy
        
    Returns:
        State machine definition
    """
    return {
        "Comment": f"EKS Upgrade workflow for {cluster_name} to version {target_version}",
        "StartAt": "PerceptionPhase",
        "States": {
            "PerceptionPhase": {
                "Type": "Task",
                "Resource": "arn:aws:states:::lambda:invoke",
                "Parameters": {
                    "FunctionName": "eks-upgrade-agent-perception",
                    "Payload": {
                        "cluster_name.$": "$.cluster_name",
                        "target_version.$": "$.target_version",
                        "phase": "perception"
                    }
                },
                "Next": "ReasoningPhase",
                "Catch": [
                    {
                        "ErrorEquals": ["States.ALL"],
                        "Next": "HandleFailure",
                        "ResultPath": "$.error"
                    }
                ]
            },
            "ReasoningPhase": {
                "Type": "Task",
                "Resource": "arn:aws:states:::lambda:invoke",
                "Parameters": {
                    "FunctionName": "eks-upgrade-agent-reasoning",
                    "Payload": {
                        "cluster_name.$": "$.cluster_name",
                        "target_version.$": "$.target_version",
                        "perception_data.$": "$.perception_data",
                        "phase": "reasoning"
                    }
                },
                "Next": "ExecutionPhase",
                "Catch": [
                    {
                        "ErrorEquals": ["States.ALL"],
                        "Next": "HandleFailure",
                        "ResultPath": "$.error"
                    }
                ]
            },
            "ExecutionPhase": {
                "Type": "Task",
                "Resource": "arn:aws:states:::lambda:invoke",
                "Parameters": {
                    "FunctionName": "eks-upgrade-agent-execution",
                    "Payload": {
                        "cluster_name.$": "$.cluster_name",
                        "target_version.$": "$.target_version",
                        "upgrade_plan.$": "$.upgrade_plan",
                        "phase": "execution"
                    }
                },
                "Next": "ValidationPhase",
                "Catch": [
                    {
                        "ErrorEquals": ["States.ALL"],
                        "Next": "HandleFailure",
                        "ResultPath": "$.error"
                    }
                ]
            },
            "ValidationPhase": {
                "Type": "Task",
                "Resource": "arn:aws:states:::lambda:invoke",
                "Parameters": {
                    "FunctionName": "eks-upgrade-agent-validation",
                    "Payload": {
                        "cluster_name.$": "$.cluster_name",
                        "target_version.$": "$.target_version",
                        "execution_result.$": "$.execution_result",
                        "phase": "validation"
                    }
                },
                "Next": "CheckValidationResult"
            },
            "CheckValidationResult": {
                "Type": "Choice",
                "Choices": [
                    {
                        "Variable": "$.validation_result.success",
                        "BooleanEquals": True,
                        "Next": "UpgradeSuccess"
                    }
                ],
                "Default": "TriggerRollback"
            },
            "UpgradeSuccess": {
                "Type": "Succeed",
                "Result": {
                    "status": "SUCCESS",
                    "message": "EKS upgrade completed successfully"
                }
            },
            "TriggerRollback": {
                "Type": "Task",
                "Resource": "arn:aws:states:::lambda:invoke",
                "Parameters": {
                    "FunctionName": "eks-upgrade-agent-rollback",
                    "Payload": {
                        "cluster_name.$": "$.cluster_name",
                        "rollback_reason.$": "$.validation_result.error",
                        "phase": "rollback"
                    }
                },
                "Next": "UpgradeFailure"
            },
            "HandleFailure": {
                "Type": "Task",
                "Resource": "arn:aws:states:::lambda:invoke",
                "Parameters": {
                    "FunctionName": "eks-upgrade-agent-rollback",
                    "Payload": {
                        "cluster_name.$": "$.cluster_name",
                        "rollback_reason.$": "$.error.Cause",
                        "phase": "rollback"
                    }
                },
                "Next": "UpgradeFailure"
            },
            "UpgradeFailure": {
                "Type": "Fail",
                "Cause": "EKS upgrade failed and rollback was triggered"
            }
        }
    }