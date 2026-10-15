import os
import boto3
import logging
import urllib.parse
from botocore.exceptions import ClientError
from typing import Optional

logger = logging.getLogger(__name__)

DOCX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

class S3Service:
    """Helper service for S3 download, upload, and presigned URL operations."""

    def __init__(self, s3_client=None, region_name: Optional[str] = None):
        self.s3_client = s3_client or boto3.client("s3", region_name=region_name)

    @staticmethod
    def decode_key(key: str) -> str:
        """
        Decode URL-encoded S3 keys (e.g. 'folder/my+file%20name.pdf' -> 'folder/my file name.pdf').
        """
        return urllib.parse.unquote_plus(key)

    def download_file(self, bucket: str, key: str, local_destination_path: str) -> str:
        """
        Download an S3 object to a local file.
        """
        clean_key = self.decode_key(key)
        logger.info(f"Downloading s3://{bucket}/{clean_key} to {local_destination_path}")
        try:
            self.s3_client.download_file(bucket, clean_key, local_destination_path)
            logger.info("Download completed successfully.")
            return local_destination_path
        except ClientError as e:
            logger.error(f"Failed to download s3://{bucket}/{clean_key}: {e}")
            raise

    def upload_file(
        self,
        local_file_path: str,
        bucket: str,
        destination_key: str,
        content_type: str = DOCX_CONTENT_TYPE,
        metadata: Optional[dict] = None
    ) -> str:
        """
        Upload a local file to S3.
        """
        extra_args = {"ContentType": content_type}
        if metadata:
            extra_args["Metadata"] = metadata

        logger.info(f"Uploading {local_file_path} to s3://{bucket}/{destination_key}")
        try:
            self.s3_client.upload_file(
                Filename=local_file_path,
                Bucket=bucket,
                Key=destination_key,
                ExtraArgs=extra_args
            )
            s3_uri = f"s3://{bucket}/{destination_key}"
            logger.info(f"Upload complete: {s3_uri}")
            return s3_uri
        except ClientError as e:
            logger.error(f"Failed to upload to s3://{bucket}/{destination_key}: {e}")
            raise

    def upload_bytes(
        self,
        data: bytes,
        bucket: str,
        destination_key: str,
        content_type: str = DOCX_CONTENT_TYPE,
        metadata: Optional[dict] = None
    ) -> str:
        """
        Upload in-memory bytes directly to S3.
        """
        extra_args = {"ContentType": content_type}
        if metadata:
            extra_args["Metadata"] = metadata

        logger.info(f"Uploading {len(data)} bytes to s3://{bucket}/{destination_key}")
        try:
            self.s3_client.put_object(
                Bucket=bucket,
                Key=destination_key,
                Body=data,
                ContentType=content_type,
                Metadata=metadata or {}
            )
            s3_uri = f"s3://{bucket}/{destination_key}"
            logger.info(f"Upload complete: {s3_uri}")
            return s3_uri
        except ClientError as e:
            logger.error(f"Failed to put object into s3://{bucket}/{destination_key}: {e}")
            raise

    def generate_presigned_url(self, bucket: str, key: str, expires_in_seconds: int = 3600) -> str:
        """
        Generate a presigned GET URL for downloading the converted file.
        """
        try:
            url = self.s3_client.generate_presigned_url(
                ClientMethod="get_object",
                Params={"Bucket": bucket, "Key": key},
                ExpiresIn=expires_in_seconds
            )
            return url
        except ClientError as e:
            logger.warning(f"Could not generate presigned URL: {e}")
            return ""
