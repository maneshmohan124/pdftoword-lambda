import os
import logging
from dataclasses import dataclass

@dataclass(frozen=True)
class AppConfig:
    """Application configuration loaded from environment variables."""
    output_s3_bucket: str = os.getenv("OUTPUT_S3_BUCKET", "")
    output_prefix: str = os.getenv("OUTPUT_PREFIX", "converted/").strip("/")
    log_level: str = os.getenv("LOG_LEVEL", "INFO").upper()
    aws_region: str = os.getenv("AWS_REGION", "us-east-1")
    temp_dir: str = os.getenv("TEMP_DIR", "/tmp")

    @classmethod
    def get_output_prefix_with_slash(cls) -> str:
        prefix = os.getenv("OUTPUT_PREFIX", "converted").strip("/")
        return f"{prefix}/" if prefix else ""

def setup_logging(log_level: str = "INFO") -> None:
    """Setup root logger configuration."""
    level = getattr(logging, log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s"
    )
