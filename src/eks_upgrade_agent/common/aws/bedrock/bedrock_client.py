"""
Amazon Bedrock client wrapper with retry logic, error handling, and cost optimization.
"""

import json
import time
from typing import Any, Dict, List, Optional

import structlog

from ...models.aws_ai import BedrockAnalysisResult, AWSAIConfig
from .rate_limiter import RateLimiter, BedrockRateLimitError
from .cost_tracker import CostTracker, BedrockCostThresholdError
from .model_invoker import ModelInvoker

logger = structlog.get_logger(__name__)


class BedrockClient:
    """
    Amazon Bedrock client wrapper with advanced features.
    
    Features:
    - Retry logic with exponential backoff
    - Rate limiting and cost optimization
    - Error handling and logging
    - Token usage tracking
    - Multiple model support
    """

    def __init__(self, config: AWSAIConfig):
        """
        Initialize Bedrock client.
        
        Args:
            config: AWS AI configuration
        """
        self.config = config
        self.logger = logger.bind(component="bedrock_client")
        
        # Initialize components
        self.rate_limiter = RateLimiter(config.max_bedrock_requests_per_minute)
        self.cost_tracker = CostTracker(config.cost_threshold_usd)
        self.model_invoker = ModelInvoker(config, self.rate_limiter, self.cost_tracker)
        
        self.logger.info(
            "Bedrock client initialized",
            model_id=config.bedrock_model_id,
            region=config.bedrock_region,
        )

    def analyze_text(
        self,
        text: str,
        prompt_template: str,
        model_id: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> BedrockAnalysisResult:
        """
        Analyze text using Bedrock model.
        
        Args:
            text: Text to analyze
            prompt_template: Prompt template to use
            model_id: Override default model ID
            max_tokens: Override default max tokens
            temperature: Override default temperature
            
        Returns:
            Analysis result
        """
        start_time = time.time()
        
        # Use defaults from config if not provided
        model_id = model_id or self.config.bedrock_model_id
        max_tokens = max_tokens or self.config.bedrock_max_tokens
        temperature = temperature or self.config.bedrock_temperature
        
        # Format prompt with text
        formatted_prompt = prompt_template.format(text=text)
        
        # Prepare request body for Claude 3
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [
                {
                    "role": "user",
                    "content": formatted_prompt,
                }
            ],
        }
        
        self.logger.info(
            "Analyzing text with Bedrock",
            model_id=model_id,
            text_length=len(text),
            max_tokens=max_tokens,
            temperature=temperature,
        )
        
        try:
            response = self.model_invoker.invoke_model(model_id, body)
            processing_time = time.time() - start_time
            
            # Extract content from Claude 3 response
            content = response.get("content", [])
            if content and isinstance(content, list) and len(content) > 0:
                analysis_text = content[0].get("text", "")
            else:
                analysis_text = ""
            
            # Parse structured response (assuming JSON format)
            try:
                analysis_data = json.loads(analysis_text)
            except json.JSONDecodeError:
                # Fallback: treat as plain text findings
                analysis_data = {
                    "findings": [analysis_text] if analysis_text else [],
                    "breaking_changes": [],
                    "deprecations": [],
                    "recommendations": [],
                    "severity_score": 5.0,
                    "confidence": 0.8,
                }
            
            # Extract token usage
            token_usage = response.get("usage", {})
            
            result = BedrockAnalysisResult(
                model_id=model_id,
                input_text=text,
                findings=analysis_data.get("findings", []),
                breaking_changes=analysis_data.get("breaking_changes", []),
                deprecations=analysis_data.get("deprecations", []),
                recommendations=analysis_data.get("recommendations", []),
                severity_score=analysis_data.get("severity_score", 5.0),
                confidence=analysis_data.get("confidence", 0.8),
                processing_time=processing_time,
                token_usage=token_usage,
            )
            
            self.logger.info(
                "Text analysis completed",
                analysis_id=result.analysis_id,
                processing_time=processing_time,
                findings_count=len(result.findings),
                severity_score=result.severity_score,
            )
            
            return result
            
        except Exception as e:
            self.logger.error(
                "Text analysis failed",
                error=str(e),
                text_length=len(text),
                model_id=model_id,
            )
            raise

    def analyze_release_notes(
        self,
        release_notes: str,
        source_version: str,
        target_version: str,
    ) -> BedrockAnalysisResult:
        """
        Analyze release notes for breaking changes and deprecations.
        
        Args:
            release_notes: Release notes text
            source_version: Current version
            target_version: Target version
            
        Returns:
            Analysis result focused on upgrade impact
        """
        from .prompt_templates import PromptTemplates
        
        prompt = PromptTemplates.RELEASE_NOTES_ANALYSIS.format(
            release_notes=release_notes,
            source_version=source_version,
            target_version=target_version,
        )
        
        return self.analyze_text(
            text=release_notes,
            prompt_template=prompt,
        )

    def make_upgrade_decision(
        self,
        cluster_state: str,
        analysis_results: List[BedrockAnalysisResult],
        target_version: str,
    ) -> BedrockAnalysisResult:
        """
        Make upgrade decision based on cluster state and analysis results.
        
        Args:
            cluster_state: Current cluster state description
            analysis_results: Previous analysis results
            target_version: Target version
            
        Returns:
            Decision analysis result
        """
        from .prompt_templates import PromptTemplates
        
        # Combine analysis results
        combined_findings = []
        combined_breaking_changes = []
        combined_deprecations = []
        
        for result in analysis_results:
            combined_findings.extend(result.findings)
            combined_breaking_changes.extend(result.breaking_changes)
            combined_deprecations.extend(result.deprecations)
        
        analysis_summary = {
            "findings": combined_findings,
            "breaking_changes": combined_breaking_changes,
            "deprecations": combined_deprecations,
        }
        
        prompt = PromptTemplates.UPGRADE_DECISION.format(
            cluster_state=cluster_state,
            analysis_summary=json.dumps(analysis_summary, indent=2),
            target_version=target_version,
        )
        
        return self.analyze_text(
            text=cluster_state,
            prompt_template=prompt,
        )

    def get_cost_summary(self) -> Dict[str, Any]:
        """
        Get cost and usage summary.
        
        Returns:
            Cost and usage statistics
        """
        cost_summary = self.cost_tracker.get_cost_summary()
        cost_summary.update({
            "requests_last_minute": self.rate_limiter.get_current_usage(),
            "rate_limit": self.config.max_bedrock_requests_per_minute,
        })
        return cost_summary