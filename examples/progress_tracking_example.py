#!/usr/bin/env python3
"""
Example demonstrating progress tracking and test artifacts management.

This example shows how to use the ProgressTracker and TestArtifactsManager
for monitoring upgrade progress and organizing test outputs.
"""

import asyncio
import tempfile
from pathlib import Path
from datetime import datetime

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from eks_upgrade_agent.common.progress import ProgressTracker
from eks_upgrade_agent.common.artifacts import TestArtifactsManager
from eks_upgrade_agent.common.models.progress import TaskType
from eks_upgrade_agent.common.models.artifacts import ArtifactType


async def main():
    """Main example function."""
    print("🚀 EKS Upgrade Agent - Progress Tracking & Test Artifacts Example")
    print("=" * 70)
    
    # Create temporary directories for the example
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Initialize Progress Tracker
        print("\n📊 Initializing Progress Tracker...")
        progress_tracker = ProgressTracker(
            upgrade_id="example-upgrade-001",
            plan_id="example-plan-001",
            cluster_name="example-cluster",
            storage_path=temp_path / "progress",
            eventbridge_bus_name="example-bus",
            enable_websocket=False  # Disabled for example
        )
        
        # Initialize Test Artifacts Manager
        print("📁 Initializing Test Artifacts Manager...")
        artifacts_manager = TestArtifactsManager(
            base_directory=temp_path / "artifacts",
            s3_bucket="example-bucket",
            s3_prefix="example-prefix",
            retention_days=7,
            auto_upload=False  # Disabled for example
        )
        
        # Start upgrade tracking
        print("\n🎯 Starting upgrade process...")
        progress_tracker.start_upgrade("Initialization")
        
        # Create test session
        session = artifacts_manager.create_session(
            upgrade_id="example-upgrade-001",
            cluster_name="example-cluster",
            session_name="Example Upgrade Session",
            description="Demonstration of progress tracking and artifacts"
        )
        
        # Create artifact collection
        collection = artifacts_manager.create_collection(
            session_id=session.session_id,
            collection_name="Upgrade Logs",
            description="Logs from the upgrade process"
        )
        
        # Simulate upgrade tasks
        tasks = [
            ("perception", "Data Collection", "Collecting cluster information"),
            ("reasoning", "Plan Generation", "Generating upgrade plan"),
            ("execution", "Infrastructure Provisioning", "Provisioning new cluster"),
            ("validation", "Health Checks", "Validating cluster health")
        ]
        
        for i, (task_id, task_name, description) in enumerate(tasks):
            print(f"\n📋 Task {i+1}/4: {task_name}")
            
            # Add task to progress tracker
            task = progress_tracker.add_task(
                task_id=task_id,
                task_name=task_name,
                task_type=TaskType.UPGRADE_STEP
            )
            
            # Start task
            progress_tracker.start_task(task_id, f"Starting {description.lower()}")
            
            # Simulate task progress
            for progress in [25, 50, 75]:
                await asyncio.sleep(0.1)  # Simulate work
                progress_tracker.update_task_progress(
                    task_id, progress, f"{description} - {progress}% complete"
                )
                print(f"  ⏳ {progress}% complete")
            
            # Create a log file for this task
            log_file = temp_path / f"{task_id}_log.txt"
            log_content = f"""
Task: {task_name}
Description: {description}
Started: {datetime.now()}
Status: Completed successfully
Progress: 100%

Detailed logs would go here...
"""
            log_file.write_text(log_content)
            
            # Add log file as artifact
            artifact = artifacts_manager.add_artifact(
                session_id=session.session_id,
                collection_id=collection.collection_id,
                file_path=log_file,
                artifact_name=f"{task_name} Log",
                artifact_type=ArtifactType.LOG_FILE,
                description=f"Log file for {task_name}",
                task_id=task_id,
                tags=["upgrade", "log", task_id]
            )
            
            # Complete task
            progress_tracker.complete_task(task_id, f"{description} completed successfully")
            print(f"  ✅ {task_name} completed")
        
        # Complete upgrade
        progress_tracker.complete_upgrade()
        artifacts_manager.complete_session(session.session_id)
        
        print("\n🎉 Upgrade process completed!")
        
        # Display progress summary
        print("\n📈 Progress Summary:")
        summary = progress_tracker.get_progress_summary()
        print(f"  • Upgrade ID: {summary['upgrade_id']}")
        print(f"  • Cluster: {summary['cluster_name']}")
        print(f"  • Status: {summary['status']}")
        print(f"  • Overall Progress: {summary['overall_percentage']:.1f}%")
        print(f"  • Total Tasks: {summary['total_tasks']}")
        print(f"  • Duration: {summary['duration']}")
        
        # Display artifacts summary
        print("\n📦 Artifacts Summary:")
        artifacts_summary = artifacts_manager.get_session_summary(session.session_id)
        if artifacts_summary:
            print(f"  • Session ID: {artifacts_summary['session_id']}")
            print(f"  • Total Artifacts: {artifacts_summary['total_artifacts']}")
            print(f"  • Total Size: {artifacts_summary['total_size_bytes']} bytes")
            print(f"  • Collections: {artifacts_summary['collections_count']}")
            
            # Show artifact types
            artifact_types = artifacts_summary['artifact_types']
            for artifact_type, count in artifact_types.items():
                if count > 0:
                    print(f"    - {artifact_type}: {count}")
        
        # Search for specific artifacts
        print("\n🔍 Searching for log artifacts:")
        log_artifacts = artifacts_manager.search_artifacts(
            session_id=session.session_id,
            artifact_type=ArtifactType.LOG_FILE
        )
        for artifact in log_artifacts:
            print(f"  • {artifact.name} ({artifact.file_size} bytes)")
            print(f"    Tags: {', '.join(artifact.tags)}")
            print(f"    Path: {artifact.local_path}")
        
        # Demonstrate event callbacks
        print("\n🔔 Event Callback Example:")
        
        def event_callback(event):
            print(f"  📢 Event: {event.message} (Task: {event.task_id})")
        
        progress_tracker.add_event_callback(event_callback)
        
        # Add one more task to show callbacks
        progress_tracker.add_task("cleanup", "Cleanup", TaskType.CLEANUP)
        progress_tracker.start_task("cleanup", "Starting cleanup operations")
        progress_tracker.complete_task("cleanup", "Cleanup completed")
        
        # Cleanup
        progress_tracker.cleanup()
        artifacts_manager.cleanup()
        
        print("\n✨ Example completed successfully!")
        print(f"📁 Temporary files were created in: {temp_path}")
        print("   (Files will be automatically cleaned up)")


if __name__ == "__main__":
    asyncio.run(main())