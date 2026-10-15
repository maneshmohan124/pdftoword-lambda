import json
import pytest
from unittest.mock import MagicMock, patch

import lambda_function


@pytest.fixture
def mock_s3_service(monkeypatch):
    mock = MagicMock()
    mock.decode_key.side_effect = lambda k: k
    mock.download_file.return_value = "/tmp/fake.pdf"
    mock.upload_file.return_value = "s3://mock-bucket/converted/sample.docx"
    mock.upload_bytes.return_value = "s3://mock-bucket/converted/sample.docx"
    mock.generate_presigned_url.return_value = "https://s3.amazonaws.com/mock-bucket/converted/sample.docx?token=xyz"
    monkeypatch.setattr(lambda_function, "s3_service", mock)
    return mock


@pytest.fixture
def mock_converter(monkeypatch):
    mock = MagicMock()
    mock.convert.return_value = "/tmp/fake.docx"
    mock.convert_bytes.return_value = ("/tmp/fake.docx", b"PK fake docx bytes")
    monkeypatch.setattr(lambda_function, "PDFToWordConverter", mock)
    return mock


def test_lambda_handler_s3_event(mock_s3_service, mock_converter):
    s3_event = {
        "Records": [
            {
                "s3": {
                    "bucket": {"name": "test-upload-bucket"},
                    "object": {"key": "uploads/document.pdf"}
                }
            }
        ]
    }

    response = lambda_function.lambda_handler(s3_event, None)
    assert response["statusCode"] == 200

    body = json.loads(response["body"])
    assert "processed" in body
    assert len(body["processed"]) == 1
    assert body["processed"][0]["status"] == "SUCCESS"
    assert body["processed"][0]["destination"] == "s3://mock-bucket/converted/sample.docx"

    # Verify download and upload calls
    mock_s3_service.download_file.assert_called_once()
    mock_s3_service.upload_file.assert_called_once()


def test_lambda_handler_ignores_converted_prefix(mock_s3_service, mock_converter):
    # Prevent infinite loop: when a converted file is uploaded to the same bucket
    s3_event = {
        "Records": [
            {
                "s3": {
                    "bucket": {"name": lambda_function.config.output_s3_bucket},
                    "object": {"key": "converted/document.pdf"}
                }
            }
        ]
    }

    response = lambda_function.lambda_handler(s3_event, None)
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    # Should not process the file
    assert len(body["processed"]) == 0
    mock_s3_service.download_file.assert_not_called()


def test_lambda_handler_ignores_non_pdf(mock_s3_service, mock_converter):
    s3_event = {
        "Records": [
            {
                "s3": {
                    "bucket": {"name": "test-upload-bucket"},
                    "object": {"key": "uploads/image.png"}
                }
            }
        ]
    }

    response = lambda_function.lambda_handler(s3_event, None)
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert len(body["processed"]) == 0
    mock_s3_service.download_file.assert_not_called()


def test_lambda_handler_api_event_with_bucket_key(mock_s3_service, mock_converter):
    api_event = {
        "httpMethod": "POST",
        "body": json.dumps({"bucket": "test-bucket", "key": "test.pdf"})
    }

    response = lambda_function.lambda_handler(api_event, None)
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert "results" in body
    assert body["results"][0]["status"] == "SUCCESS"


def test_lambda_handler_invalid_payload():
    response = lambda_function.lambda_handler({"unknown": 123}, None)
    assert response["statusCode"] == 400
