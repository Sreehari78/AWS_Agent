"""
AWS S3 client for artifact storage.
"""

import logging
from typing import Optional, Dict, Any
from pathlib import Path

import boto3
from botocore.exceptions import ClientError, NoCredentialsError

from ..models.artifacts import TestArtifact, ArtifactStatus
from ..logging.utils import log_exception

logger = logging.getLogger(__name__)


class S3ArtifactClient:
    """AWS S3 client for artifact storage operations."""
    
    def __init__(self, aws_region: str = "us-east-1"):
        """
        Initialize S3 client.
        
        Args:
            aws_region: AWS region for S3 operations
        """
        self.aws_region = aws_region
        self._s3_client: Optional[boto3.client] = None
    
    @property
    def s3_client(self) -> Optional[boto3.client]:
        """Get or create S3 client."""
        if self._s3_client is None:
            try:
                self._s3_client = boto3.client('s3', region_name=self.aws_region)
            except (NoCredentialsError, ClientError) as e:
                log_exception(logger, e, "Failed to create S3 client")
        return self._s3_client
    
    def upload_artifact(self, artifact: TestArtifact) -> bool:
        """
        Upload an artifact to S3.
        
        Args:
            artifact: Artifact to upload
            
        Returns:
            True if upload successful, False otherwise
        """
        if not self.s3_client:
            logger.warning("S3 client not available")
            return False
        
        if not artifact.s3_bucket or not artifact.s3_key:
            logger.warning(f"S3 configuration missing for artifact {artifact.artifact_id}")
            return False
        
        try:
            # Prepare metadata
            metadata = self._prepare_metadata(artifact)
            
            # Upload file to S3
            self.s3_client.upload_file(
                artifact.local_path,
                artifact.s3_bucket,
                artifact.s3_key,
                ExtraArgs={'Metadata': metadata}
            )
            
            # Generate S3 URL
            s3_url = f"s3://{artifact.s3_bucket}/{artifact.s3_key}"
            artifact.mark_uploaded(s3_url)
            
            logger.info(f"Uploaded artifact {artifact.artifact_id} to S3: {s3_url}")
            return True
            
        except Exception as e:
            log_exception(logger, e, f"Failed to upload artifact {artifact.artifact_id}")
            artifact.mark_failed(str(e))
            return False
    
    def download_artifact(self, artifact: TestArtifact, local_path: str) -> bool:
        """
        Download an artifact from S3.
        
        Args:
            artifact: Artifact to download
            local_path: Local path to save file
            
        Returns:
            True if download successful, False otherwise
        """
        if not self.s3_client:
            logger.warning("S3 client not available")
            return False
        
        if not artifact.s3_bucket or not artifact.s3_key:
            logger.warning(f"S3 configuration missing for artifact {artifact.artifact_id}")
            return False
        
        try:
            # Ensure local directory exists
            Path(local_path).parent.mkdir(parents=True, exist_ok=True)
            
            # Download file from S3
            self.s3_client.download_file(
                artifact.s3_bucket,
                artifact.s3_key,
                local_path
            )
            
            logger.info(f"Downloaded artifact {artifact.artifact_id} from S3 to {local_path}")
            return True
            
        except Exception as e:
            log_exception(logger, e, f"Failed to download artifact {artifact.artifact_id}")
            return False
    
    def delete_artifact(self, artifact: TestArtifact) -> bool:
        """
        Delete an artifact from S3.
        
        Args:
            artifact: Artifact to delete
            
        Returns:
            True if deletion successful, False otherwise
        """
        if not self.s3_client:
            logger.warning("S3 client not available")
            return False
        
        if not artifact.s3_bucket or not artifact.s3_key:
            logger.warning(f"S3 configuration missing for artifact {artifact.artifact_id}")
            return False
        
        try:
            # Delete object from S3
            self.s3_client.delete_object(
                Bucket=artifact.s3_bucket,
                Key=artifact.s3_key
            )
            
            logger.info(f"Deleted artifact {artifact.artifact_id} from S3")
            return True
            
        except Exception as e:
            log_exception(logger, e, f"Failed to delete artifact {artifact.artifact_id}")
            return False
    
    def check_artifact_exists(self, artifact: TestArtifact) -> bool:
        """
        Check if an artifact exists in S3.
        
        Args:
            artifact: Artifact to check
            
        Returns:
            True if artifact exists, False otherwise
        """
        if not self.s3_client:
            return False
        
        if not artifact.s3_bucket or not artifact.s3_key:
            return False
        
        try:
            self.s3_client.head_object(
                Bucket=artifact.s3_bucket,
                Key=artifact.s3_key
            )
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            log_exception(logger, e, f"Error checking artifact {artifact.artifact_id}")
            return False
        except Exception as e:
            log_exception(logger, e, f"Error checking artifact {artifact.artifact_id}")
            return False
    
    def _prepare_metadata(self, artifact: TestArtifact) -> Dict[str, str]:
        """
        Prepare S3 metadata for artifact.
        
        Args:
            artifact: Artifact to prepare metadata for
            
        Returns:
            Dictionary of metadata
        """
        return {
            'artifact-id': artifact.artifact_id,
            'artifact-type': str(artifact.artifact_type),
            'upgrade-id': artifact.upgrade_id or '',
            'task-id': artifact.task_id or '',
            'file-hash': artifact.file_hash or ''
        }