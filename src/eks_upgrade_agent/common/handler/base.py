"""
Base exception class for the EKS Upgrade Agent.
"""

import traceback
from datetime import datetime, timezone
from typing import Any, Dict, Optional


class EKSUpgradeAgentError(Exception):
    """
    Base exception class for all EKS Upgrade Agent errors.
    
    Provides common functionality for error context preservation,
    structured error data, and integration with logging systems.
    """
    
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
        recoverable: bool = False
    ):
        """
        Initialize the base exception with comprehensive error information.
        
        Args:
            message: Human-readable error description
            error_code: Machine-readable error identifier
            context: Additional context data for debugging
            cause: Original exception that caused this error
            recoverable: Whether this error can be recovered from
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.context = context or {}
        self.cause = cause
        self.recoverable = recoverable
        self.timestamp = datetime.now(timezone.utc)
        self.stack_trace = traceback.format_exc()
        
        # Preserve the original exception chain
        if cause:
            self.__cause__ = cause
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert exception to dictionary for structured logging.
        
        Returns:
            Dictionary representation of the exception with all context
        """
        return {
            "error_type": self.__class__.__name__,
            "error_code": self.error_code,
            "message": self.message,
            "context": self.context,
            "recoverable": self.recoverable,
            "timestamp": self.timestamp.isoformat(),
            "stack_trace": self.stack_trace,
            "cause": str(self.cause) if self.cause else None,
            "cause_type": type(self.cause).__name__ if self.cause else None
        }
    
    def add_context(self, key: str, value: Any) -> "EKSUpgradeAgentError":
        """
        Add additional context to the exception.
        
        Args:
            key: Context key
            value: Context value
            
        Returns:
            Self for method chaining
        """
        self.context[key] = value
        return self
    
    def __str__(self) -> str:
        """String representation including error code and context."""
        context_str = f" (Context: {self.context})" if self.context else ""
        return f"[{self.error_code}] {self.message}{context_str}"