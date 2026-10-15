import os
import sys
import json
import uuid
import base64
import logging
from pathlib import Path
from typing import Dict, Any, List

# Ensure cv2 is available (uses lightweight shim if opencv binary was omitted)
try:
    import cv2
except ImportError:
    from src import cv2_shim
    sys.modules["cv2"] = cv2_shim

from src.config import AppConfig, setup_logging
from src.s3_service import S3Service
from src.converter import PDFToWordConverter, PDFConversionError

# Initialize logging and configuration
config = AppConfig()
setup_logging(config.log_level)
logger = logging.getLogger("lambda_function")

s3_service = S3Service(region_name=config.aws_region)


def _determine_output_key(input_key: str, output_prefix: str) -> str:
    """
    Given an input key like 'uploads/contracts/sample.pdf' and output_prefix 'converted/',
    returns 'converted/contracts/sample.docx' or 'converted/sample.docx'.
    """
    path = Path(input_key)
    filename_without_ext = path.stem
    docx_filename = f"{filename_without_ext}.docx"
    
    # Strip leading folders if desired, or mirror structure
    prefix = output_prefix.strip("/")
    if prefix:
        return f"{prefix}/{docx_filename}"
    return docx_filename


def handle_s3_event(event: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Process AWS S3 ObjectCreated events.
    Downloads PDF, converts to Word DOCX, and uploads back to S3.
    """
    results = []
    output_prefix = config.get_output_prefix_with_slash()

    for record in event.get("Records", []):
        s3_data = record.get("s3", {})
        source_bucket = s3_data.get("bucket", {}).get("name")
        raw_key = s3_data.get("object", {}).get("key")

        if not source_bucket or not raw_key:
            logger.warning("Record missing bucket or object key. Skipping.")
            continue

        source_key = s3_service.decode_key(raw_key)

        dest_bucket = config.output_s3_bucket if config.output_s3_bucket else source_bucket

        # Infinite loop prevention: don't process files already in the output directory if using same bucket
        if dest_bucket == source_bucket and output_prefix and source_key.startswith(output_prefix):
            logger.info(f"Skipping key {source_key} as it is already in the output prefix '{output_prefix}'.")
            continue

        # Check for PDF extension
        if not source_key.lower().endswith(".pdf"):
            logger.info(f"Skipping key {source_key}: not a PDF file.")
            continue

        dest_key = _determine_output_key(source_key, output_prefix)

        job_id = str(uuid.uuid4())[:8]
        local_pdf_path = os.path.join(config.temp_dir, f"{job_id}_input.pdf")
        local_docx_path = os.path.join(config.temp_dir, f"{job_id}_converted.docx")

        try:
            logger.info(f"Processing S3 file: s3://{source_bucket}/{source_key} -> s3://{dest_bucket}/{dest_key}")
            # 1. Download PDF from S3
            s3_service.download_file(source_bucket, source_key, local_pdf_path)

            # 2. Convert PDF to DOCX
            PDFToWordConverter.convert(local_pdf_path, local_docx_path)

            # 3. Upload DOCX to S3
            s3_uri = s3_service.upload_file(
                local_file_path=local_docx_path,
                bucket=dest_bucket,
                destination_key=dest_key,
                metadata={
                    "source-bucket": source_bucket,
                    "source-key": source_key,
                    "converted-by": "lambda-pdf2docx"
                }
            )

            # 4. Generate presigned download URL (optional)
            presigned_url = s3_service.generate_presigned_url(dest_bucket, dest_key)

            results.append({
                "status": "SUCCESS",
                "source": f"s3://{source_bucket}/{source_key}",
                "destination": s3_uri,
                "download_url": presigned_url
            })
        except Exception as e:
            logger.error(f"Error processing s3://{source_bucket}/{source_key}: {e}", exc_info=True)
            results.append({
                "status": "FAILED",
                "source": f"s3://{source_bucket}/{source_key}",
                "error": str(e)
            })
        finally:
            # Clean up local temporary files
            for temp_file in [local_pdf_path, local_docx_path]:
                if os.path.exists(temp_file):
                    try:
                        os.remove(temp_file)
                    except OSError:
                        pass

    return results


def handle_api_request(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle direct HTTP / API Gateway / Function URL requests.
    Supports Base64-encoded PDF uploads or JSON specifying bucket/key.
    """
    body = event.get("body", "")
    is_base64 = event.get("isBase64Encoded", False)

    if not body:
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "Request body cannot be empty."})
        }

    # Case 1: Body is JSON payload
    try:
        parsed_body = json.loads(body) if isinstance(body, str) else body
    except json.JSONDecodeError:
        parsed_body = None

    dest_bucket = config.output_s3_bucket

    if isinstance(parsed_body, dict):
        # Subcase 1a: Bucket & Key provided in JSON
        if "bucket" in parsed_body and "key" in parsed_body:
            mock_s3_event = {
                "Records": [{
                    "s3": {
                        "bucket": {"name": parsed_body["bucket"]},
                        "object": {"key": parsed_body["key"]}
                    }
                }]
            }
            results = handle_s3_event(mock_s3_event)
            status_code = 200 if results and results[0]["status"] == "SUCCESS" else 500
            return {
                "statusCode": status_code,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"results": results})
            }

        # Subcase 1b: Base64 PDF embedded in JSON {"pdf_base64": "...", "filename": "sample.pdf"}
        if "pdf_base64" in parsed_body:
            filename = parsed_body.get("filename", f"document_{uuid.uuid4().hex[:6]}.pdf")
            try:
                pdf_bytes = base64.b64decode(parsed_body["pdf_base64"])
            except Exception as e:
                return {
                    "statusCode": 400,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({"error": f"Invalid base64 encoding: {e}"})
                }
            return _process_and_upload_bytes(pdf_bytes, filename)

    # Case 2: Direct raw binary/base64 upload in body
    if is_base64:
        try:
            pdf_bytes = base64.b64decode(body)
            filename = f"upload_{uuid.uuid4().hex[:8]}.pdf"
            return _process_and_upload_bytes(pdf_bytes, filename)
        except Exception as e:
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": f"Failed to decode base64 body: {e}"})
            }

    return {
        "statusCode": 400,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({
            "error": "Unrecognized request format. Provide S3 event, JSON with bucket/key or pdf_base64, or binary body."
        })
    }


def _process_and_upload_bytes(pdf_bytes: bytes, filename: str) -> Dict[str, Any]:
    dest_bucket = config.output_s3_bucket
    if not dest_bucket:
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "OUTPUT_S3_BUCKET environment variable is not configured."})
        }

    output_prefix = config.get_output_prefix_with_slash()
    dest_key = _determine_output_key(filename, output_prefix)

    try:
        temp_docx, docx_bytes = PDFToWordConverter.convert_bytes(pdf_bytes, config.temp_dir)
        s3_uri = s3_service.upload_bytes(docx_bytes, dest_bucket, dest_key)
        presigned_url = s3_service.generate_presigned_url(dest_bucket, dest_key)

        if os.path.exists(temp_docx):
            try:
                os.remove(temp_docx)
            except OSError:
                pass

        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "message": "Conversion successful",
                "destination": s3_uri,
                "s3_bucket": dest_bucket,
                "s3_key": dest_key,
                "download_url": presigned_url
            })
        }
    except Exception as e:
        logger.error(f"Error converting uploaded PDF bytes: {e}", exc_info=True)
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": str(e)})
        }


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    AWS Lambda entrypoint handler.
    Automatically identifies whether the invocation is from an S3 Event or API Gateway / HTTP request.
    """
    logger.info(f"Lambda triggered with event keys: {list(event.keys())}")

    # Check for S3 trigger event
    if "Records" in event and len(event["Records"]) > 0 and "s3" in event["Records"][0]:
        logger.info("Handling S3 event notification.")
        results = handle_s3_event(event)
        return {
            "statusCode": 200,
            "body": json.dumps({"processed": results})
        }

    # Check for API Gateway / Function URL event
    if "httpMethod" in event or "rawPath" in event or "requestContext" in event:
        logger.info("Handling HTTP/API Gateway event.")
        return handle_api_request(event)

    # Direct custom invocation (e.g. CLI or console test with bucket & key)
    if "bucket" in event and "key" in event:
        logger.info("Handling direct invocation with bucket and key.")
        mock_s3_event = {
            "Records": [{
                "s3": {
                    "bucket": {"name": event["bucket"]},
                    "object": {"key": event["key"]}
                }
            }]
        }
        results = handle_s3_event(mock_s3_event)
        return {
            "statusCode": 200,
            "body": json.dumps({"processed": results})
        }

    logger.warning("Unrecognized event format.")
    return {
        "statusCode": 400,
        "body": json.dumps({
            "error": "Invalid invocation payload.",
            "supported_events": ["S3 Event Notification", "API Gateway/Function URL", "Direct JSON {bucket, key}"]
        })
    }
