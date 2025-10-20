#!/usr/bin/env python3
"""
AWS Orchestration Services Integration Example

This example demonstrates how to use the EKS Upgrade Agent's AWS orchestration
services including Step Functions, EventBridge, Systems Manager, and Lambda templates.
"""

import asyncio
import json
import time
from datetime import datetime, UTC
from typing import Dict, Any

from src.eks_upgrade_agent.common.aws.orchestration import (
    # Step Functions
    StepFunctionsClient,
    StateMachineDefinition,
    create_upgrade_state_machine_definition,
    
    # EventBridge
    EventBridgeClient,
    UpgradeEvent,
    create_upgrade_monitoring_rule,
    create_rollback_trigger_rule,
    
    # Systems Manager
    SSMClient,
    ParameterConfig,
    create_default_agent_config,
    
    # Lambda Templates
    LambdaTemplateManager,
    get_all_lambda_templates
)


class AWSOrchestrationDemo:
    """
    Demonstration of AWS orchestration services integration.
    
    This class shows how to use all the orchestration components together
    to create a complete EKS upgrade workflow.
    """
    
    def __init__(self, region: str = "us-east-1"):
        """Initialize the demo with AWS clients."""
        self.region = region
        
        # Initialize AWS service clients
        self.step_functions = StepFunctionsClient(region=region)
        self.eventbridge = EventBridgeClient(region=region)
        self.ssm = SSMClient(region=region)
        self.lambda_manager = LambdaTemplateManager(region=region)
        
        print(f"🚀 Initialized AWS Orchestration Demo for region: {region}")
    
    def demo_ssm_configuration(self) -> None:
        """Demonstrate SSM Parameter Store configuration management."""
        print("\n📋 SSM Parameter Store Configuration Demo")
        print("=" * 50)
        
        try:
            # Create default agent configuration
            config = create_default_agent_config()
            print(f"✅ Created default configuration with {len(config)} sections")
            
            # Store configuration in SSM
            print("📤 Storing configuration in SSM Parameter Store...")
            results = self.ssm.put_configuration(config, "demo-config")
            print(f"✅ Stored {len(results)} parameters")
            
            # Store individual parameters
            print("📤 Storing individual parameters...")
            
            # Store a regular parameter
            param_config = ParameterConfig(
                name="demo/cluster-name",
                value="demo-eks-cluster",
                type="String",
                description="Demo EKS cluster name",
                tags={"Environment": "demo", "Component": "eks-upgrade-agent"}
            )
            version = self.ssm.put_parameter(param_config)
            print(f"✅ Stored parameter 'demo/cluster-name' version {version}")
            
            # Store a secure parameter
            secret_config = ParameterConfig(
                name="demo/api-key",
                value="demo-secret-key-12345",
                type="SecureString",
                description="Demo API key (encrypted)",
                tags={"Environment": "demo", "Sensitive": "true"}
            )
            version = self.ssm.put_parameter(secret_config)
            print(f"✅ Stored secure parameter 'demo/api-key' version {version}")
            
            # Retrieve parameters
            print("📥 Retrieving parameters...")
            
            cluster_param = self.ssm.get_parameter("demo/cluster-name")
            print(f"✅ Retrieved cluster name: {cluster_param.value}")
            
            api_key_param = self.ssm.get_parameter("demo/api-key")
            print(f"✅ Retrieved API key: {api_key_param.value[:10]}...")
            
            # Retrieve configuration
            print("📥 Retrieving full configuration...")
            retrieved_config = self.ssm.get_configuration("demo-config")
            print(f"✅ Retrieved configuration with agent name: {retrieved_config['agent']['name']}")
            
            # List parameters
            print("📋 Listing parameters...")
            params = self.ssm.list_parameters("demo/")
            print(f"✅ Found {len(params)} parameters with 'demo/' prefix")
            
        except Exception as e:
            print(f"❌ SSM Demo failed: {e}")
    
    def demo_eventbridge_events(self) -> None:
        """Demonstrate EventBridge event publishing and rules."""
        print("\n📡 EventBridge Events Demo")
        print("=" * 50)
        
        try:
            # Publish upgrade events
            print("📤 Publishing upgrade events...")
            
            # Upgrade started event
            event_id = self.eventbridge.publish_upgrade_started(
                cluster_name="demo-cluster",
                target_version="1.29",
                strategy="blue_green"
            )
            print(f"✅ Published upgrade started event: {event_id}")
            
            # Phase events
            event_id = self.eventbridge.publish_phase_started(
                cluster_name="demo-cluster",
                phase="perception",
                details={"step": "collecting_cluster_info"}
            )
            print(f"✅ Published phase started event: {event_id}")
            
            event_id = self.eventbridge.publish_phase_completed(
                cluster_name="demo-cluster",
                phase="perception",
                details={"duration": 45.2, "nodes_found": 3}
            )
            print(f"✅ Published phase completed event: {event_id}")
            
            # Traffic shifting event
            event_id = self.eventbridge.publish_traffic_shifted(
                cluster_name="demo-cluster",
                percentage=25,
                target_cluster="demo-cluster-green"
            )
            print(f"✅ Published traffic shifted event: {event_id}")
            
            # Validation events
            event_id = self.eventbridge.publish_validation_result(
                cluster_name="demo-cluster",
                success=True,
                metrics={"error_rate": 0.01, "latency_p99": 150}
            )
            print(f"✅ Published validation success event: {event_id}")
            
            # Upgrade completed event
            event_id = self.eventbridge.publish_upgrade_completed(
                cluster_name="demo-cluster",
                target_version="1.29",
                duration_seconds=1800.5
            )
            print(f"✅ Published upgrade completed event: {event_id}")
            
            # Create monitoring rules
            print("📋 Creating EventBridge rules...")
            
            monitoring_rule = create_upgrade_monitoring_rule("demo-cluster")
            print(f"✅ Created monitoring rule: {monitoring_rule.name}")
            
            rollback_rule = create_rollback_trigger_rule()
            print(f"✅ Created rollback trigger rule: {rollback_rule.name}")
            
        except Exception as e:
            print(f"❌ EventBridge Demo failed: {e}")
    
    def demo_lambda_templates(self) -> None:
        """Demonstrate Lambda function templates."""
        print("\n🔧 Lambda Templates Demo")
        print("=" * 50)
        
        try:
            # Get all Lambda templates
            templates = get_all_lambda_templates()
            print(f"✅ Generated {len(templates)} Lambda function templates")
            
            for template in templates:
                print(f"  📦 {template.function_name}")
                print(f"     Runtime: {template.runtime}")
                print(f"     Memory: {template.memory_size}MB")
                print(f"     Timeout: {template.timeout}s")
                print(f"     Phase: {template.tags.get('Phase', 'unknown')}")
                
                # Show code snippet
                code_lines = template.code.split('\n')
                first_function_line = next(
                    (i for i, line in enumerate(code_lines) if 'def lambda_handler' in line),
                    0
                )
                if first_function_line < len(code_lines) - 5:
                    print(f"     Code preview:")
                    for i in range(first_function_line, min(first_function_line + 3, len(code_lines))):
                        print(f"       {code_lines[i].strip()}")
                print()
            
            # Create deployment package for one template
            print("📦 Creating deployment package...")
            perception_template = next(
                t for t in templates if "perception" in t.function_name
            )
            
            zip_content = self.lambda_manager.create_function_zip(
                perception_template.code,
                requirements=["boto3>=1.26.0", "pydantic>=2.0.0"]
            )
            print(f"✅ Created deployment package: {len(zip_content)} bytes")
            
        except Exception as e:
            print(f"❌ Lambda Templates Demo failed: {e}")
    
    def demo_step_functions_workflow(self) -> None:
        """Demonstrate Step Functions state machine creation."""
        print("\n🔄 Step Functions Workflow Demo")
        print("=" * 50)
        
        try:
            # Create upgrade state machine definition
            print("📋 Creating upgrade state machine definition...")
            
            definition_dict = create_upgrade_state_machine_definition(
                cluster_name="demo-cluster",
                target_version="1.29",
                strategy="blue_green"
            )
            
            definition = StateMachineDefinition(
                name="demo-eks-upgrade-workflow",
                definition=definition_dict,
                role_arn="arn:aws:iam::123456789012:role/demo-step-functions-role",
                timeout_seconds=3600,
                tags={
                    "Environment": "demo",
                    "Component": "eks-upgrade-agent",
                    "Purpose": "upgrade-orchestration"
                }
            )
            
            print(f"✅ Created state machine definition: {definition.name}")
            print(f"   States: {len(definition.definition['States'])}")
            print(f"   Start state: {definition.definition['StartAt']}")
            print(f"   Timeout: {definition.timeout_seconds}s")
            
            # Show state machine structure
            print("\n📊 State Machine Structure:")
            states = definition.definition['States']
            for state_name, state_config in states.items():
                state_type = state_config.get('Type', 'Unknown')
                next_state = state_config.get('Next', 'END')
                print(f"  {state_name} ({state_type}) → {next_state}")
            
            # Simulate execution input
            print("\n📥 Sample execution input:")
            execution_input = {
                "cluster_name": "demo-cluster",
                "target_version": "1.29",
                "strategy": "blue_green",
                "timestamp": datetime.now(UTC).isoformat(),
                "initiated_by": "demo-user"
            }
            print(json.dumps(execution_input, indent=2))
            
        except Exception as e:
            print(f"❌ Step Functions Demo failed: {e}")
    
    def demo_integration_workflow(self) -> None:
        """Demonstrate complete integration workflow."""
        print("\n🔗 Complete Integration Workflow Demo")
        print("=" * 50)
        
        try:
            cluster_name = "demo-integration-cluster"
            target_version = "1.29"
            
            print(f"🎯 Simulating upgrade workflow for {cluster_name} → {target_version}")
            
            # Step 1: Store configuration
            print("\n1️⃣ Storing upgrade configuration...")
            upgrade_config = {
                "cluster_name": cluster_name,
                "target_version": target_version,
                "strategy": "blue_green",
                "traffic_shift_intervals": [10, 25, 50, 75, 100],
                "validation_timeout": 300,
                "rollback_timeout": 600
            }
            
            config_results = self.ssm.put_configuration(upgrade_config, f"upgrade-{cluster_name}")
            print(f"✅ Stored {len(config_results)} configuration parameters")
            
            # Step 2: Publish upgrade started event
            print("\n2️⃣ Publishing upgrade started event...")
            event_id = self.eventbridge.publish_upgrade_started(
                cluster_name=cluster_name,
                target_version=target_version,
                strategy="blue_green"
            )
            print(f"✅ Published event: {event_id}")
            
            # Step 3: Simulate workflow phases
            phases = ["perception", "reasoning", "execution", "validation"]
            
            for i, phase in enumerate(phases, 3):
                print(f"\n{i}️⃣ Simulating {phase} phase...")
                
                # Phase started
                self.eventbridge.publish_phase_started(
                    cluster_name=cluster_name,
                    phase=phase,
                    details={"step": f"{phase}_initialization"}
                )
                
                # Simulate phase work
                time.sleep(0.5)  # Simulate processing time
                
                # Phase completed
                self.eventbridge.publish_phase_completed(
                    cluster_name=cluster_name,
                    phase=phase,
                    details={
                        "duration": 30.0 + i * 10,
                        "status": "success",
                        "artifacts_generated": i * 2
                    }
                )
                
                print(f"✅ Completed {phase} phase")
            
            # Step 7: Simulate traffic shifting
            print("\n7️⃣ Simulating traffic shifting...")
            for percentage in [10, 25, 50, 75, 100]:
                self.eventbridge.publish_traffic_shifted(
                    cluster_name=cluster_name,
                    percentage=percentage,
                    target_cluster=f"{cluster_name}-green"
                )
                print(f"✅ Shifted {percentage}% traffic to green cluster")
                time.sleep(0.2)
            
            # Step 8: Final validation and completion
            print("\n8️⃣ Final validation and completion...")
            self.eventbridge.publish_validation_result(
                cluster_name=cluster_name,
                success=True,
                metrics={
                    "error_rate": 0.005,
                    "latency_p99": 145,
                    "availability": 99.99,
                    "throughput": 1250
                }
            )
            
            self.eventbridge.publish_upgrade_completed(
                cluster_name=cluster_name,
                target_version=target_version,
                duration_seconds=1650.0
            )
            
            print(f"✅ Upgrade workflow completed successfully!")
            
            # Step 9: Retrieve final configuration
            print("\n9️⃣ Retrieving final configuration...")
            final_config = self.ssm.get_configuration(f"upgrade-{cluster_name}")
            print(f"✅ Retrieved configuration for cluster: {final_config['cluster_name']}")
            print(f"   Target version: {final_config['target_version']}")
            print(f"   Strategy: {final_config['strategy']}")
            
        except Exception as e:
            print(f"❌ Integration Workflow Demo failed: {e}")
    
    def run_all_demos(self) -> None:
        """Run all demonstration scenarios."""
        print("🎬 AWS Orchestration Services Demo")
        print("=" * 60)
        print("This demo showcases the EKS Upgrade Agent's AWS orchestration capabilities")
        print("including Step Functions, EventBridge, Systems Manager, and Lambda templates.")
        print()
        
        try:
            # Run individual demos
            self.demo_ssm_configuration()
            self.demo_eventbridge_events()
            self.demo_lambda_templates()
            self.demo_step_functions_workflow()
            self.demo_integration_workflow()
            
            print("\n🎉 All demos completed successfully!")
            print("\n📊 Summary:")
            print("✅ SSM Parameter Store - Configuration management")
            print("✅ EventBridge - Event-driven coordination")
            print("✅ Lambda Templates - Serverless execution")
            print("✅ Step Functions - Workflow orchestration")
            print("✅ Integration Workflow - Complete end-to-end flow")
            
        except Exception as e:
            print(f"\n❌ Demo execution failed: {e}")
            raise


def main():
    """Main entry point for the demo."""
    print("Starting AWS Orchestration Services Demo...")
    
    try:
        # Create and run demo
        demo = AWSOrchestrationDemo(region="us-east-1")
        demo.run_all_demos()
        
    except KeyboardInterrupt:
        print("\n⏹️ Demo interrupted by user")
    except Exception as e:
        print(f"\n💥 Demo failed with error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())