"""Remote GPU fine-tune orchestration (SSH + train.sh)."""

from voice_platform.cloud_train.config import is_cloud_train_configured
from voice_platform.cloud_train.orchestrator import CloudTrainOrchestrator

__all__ = ["CloudTrainOrchestrator", "is_cloud_train_configured"]
