# Serverless PDF to Word (.docx) Converter (Python 3.14 on AWS Lambda)

A serverless application built with **Python 3.14** that automatically converts uploaded PDF documents into editable Word (`.docx`) files and stores them in **Amazon S3**.

This project supports:
- **Automatic S3 Trigger**: Whenever a user uploads a PDF to an S3 bucket (e.g. `uploads/`), Lambda processes it and uploads the converted `.docx` to `converted/`.
- **Direct API / HTTP Upload**: Can also be invoked directly or via AWS Lambda Function URL / API Gateway with Base64-encoded PDF files.
- **GitHub Actions CI/CD**: Automatic build, package, and deployment of code updates to your manually created AWS Lambda function.

---

## Architecture Diagram

```
[ User ]
   │
   ├─► 1. Uploads "sample.pdf" to S3 (s3://my-bucket/uploads/sample.pdf)
   │
[ Amazon S3 ]
   │
   └─► 2. S3 ObjectCreated Event triggers Lambda
          │
     [ AWS Lambda (Python 3.14) ]
          │
          ├─► 3. Downloads PDF to /tmp
          ├─► 4. Converts PDF -> DOCX (using pdf2docx with fallback)
          ├─► 5. Uploads "sample.docx" to S3 (s3://my-bucket/converted/sample.docx)
          └─► 6. Cleans up /tmp temporary storage
```

---

## Project Structure

```
lambda-py/
├── .github/
│   └── workflows/
│       └── deploy.yml            # GitHub Actions CI/CD workflow
├── src/
│   ├── __init__.py
│   ├── config.py                 # Environment variables & logger configuration
│   ├── converter.py              # PDF to DOCX conversion logic (pdf2docx + fallback)
│   └── s3_service.py             # S3 download, upload, and presigned URL operations
├── sample_events/
│   ├── s3_event.json             # Sample S3 trigger event for AWS Console testing
│   ├── api_event.json            # Sample API Gateway event
│   └── direct_event.json         # Sample direct JSON invocation payload
├── tests/
│   ├── test_converter.py         # Unit tests for converter engine
│   └── test_lambda_function.py   # Unit tests for Lambda handler & S3 events
├── lambda_function.py            # Main AWS Lambda entrypoint handler
├── local_test.py                 # CLI script to test conversion locally
├── requirements.txt              # Production dependencies
├── requirements-dev.txt          # Development & test dependencies
├── .env.example                  # Example local environment settings
├── .gitignore                    # Git ignore file
└── README.md                     # Complete setup and deployment guide
```

---

## Step 1: Initial AWS Setup (Manual Creation)

You will initially create the AWS S3 Bucket and Lambda Function in the AWS Management Console:

### 1. Create S3 Bucket
1. Open the **Amazon S3 Console** (`https://console.aws.amazon.com/s3/`).
2. Click **Create bucket**.
3. Choose a bucket name (e.g. `my-pdf-converter-bucket-12345`) and select your AWS Region (e.g. `us-east-1`).
4. Keep **Block all public access** checked (recommended for security).
5. Click **Create bucket**.
6. (Optional) In the bucket, create two folders:
   - `uploads/` (where users upload PDFs)
   - `converted/` (where converted Word documents will be saved)

---

### 2. Create IAM Role for Lambda
1. Open the **IAM Console** (`https://console.aws.amazon.com/iam/`).
2. Go to **Roles** -> **Create role**.
3. Select **AWS service** and choose **Lambda** as the use case.
4. Add the following permissions:
   - `AWSLambdaBasicExecutionRole` (allows CloudWatch Logs)
5. Add inline policy or attach S3 policy for your bucket:
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Action": [
           "s3:GetObject",
           "s3:PutObject",
           "s3:ListBucket"
         ],
         "Resource": [
           "arn:aws:s3:::my-pdf-converter-bucket-12345",
           "arn:aws:s3:::my-pdf-converter-bucket-12345/*"
         ]
       }
     ]
   }
   ```
6. Name the role `pdf-to-word-lambda-role` and click **Create role**.

---

### 3. Create Lambda Function Manually
1. Open the **AWS Lambda Console** (`https://console.aws.amazon.com/lambda/`).
2. Click **Create function** -> **Author from scratch**.
3. Function name: `pdf-to-word-converter`.
4. Runtime: Choose **Python 3.14** (or Python runtime of your choice).
5. Architecture: **x86_64**.
6. Execution role: **Use an existing role** -> Select `pdf-to-word-lambda-role`.
7. Click **Create function**.

#### Configure Function Settings:
- **General Configuration**:
  - Memory: **1024 MB** (or 2048 MB for large PDFs).
  - Timeout: **2 minutes** (120 seconds).
  - Ephemeral storage (`/tmp`): **1024 MB**.
- **Environment Variables**:
  - `OUTPUT_S3_BUCKET`: `my-pdf-converter-bucket-12345` (optional, defaults to source bucket if blank).
  - `OUTPUT_PREFIX`: `converted/`
  - `LOG_LEVEL`: `INFO`

---

### 4. Configure S3 Event Notification Trigger
1. In your Lambda function, click **Add trigger**.
2. Select **S3**.
3. Choose your bucket: `my-pdf-converter-bucket-12345`.
4. Event types: `All object create events` (`s3:ObjectCreated:*`).
5. **Prefix**: `uploads/` (IMPORTANT: Prevents infinite loops!).
6. **Suffix**: `.pdf`
7. Check the recursive invocation acknowledgment checkbox.
8. Click **Add**.

---

## Step 2: Configure GitHub Actions for Automated Deployment

Whenever you push changes to your `main` branch, GitHub Actions will automatically install dependencies, package the application, and update your AWS Lambda function code.

### Configure GitHub Secrets:
1. In your GitHub repository, navigate to **Settings** -> **Secrets and variables** -> **Actions**.
2. Click **New repository secret** and add:

| Secret Name | Value Example | Description |
|---|---|---|
| `AWS_ACCESS_KEY_ID` | `AKIA...` | IAM User Access Key with Lambda deploy permissions |
| `AWS_SECRET_ACCESS_KEY` | `wJalr...` | IAM User Secret Key |
| `AWS_REGION` | `us-east-1` | AWS Region of your Lambda function |
| `LAMBDA_FUNCTION_NAME` | `pdf-to-word-converter` | The exact Lambda function name created in Step 1 |
| `DEPLOYMENT_BUCKET` | `my-pdf-converter-bucket-12345` | (Optional) Used if deployment package exceeds 50MB |

#### Minimal IAM Permissions for GitHub Actions Deployer:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "lambda:UpdateFunctionCode",
        "lambda:GetFunction",
        "lambda:GetFunctionConfiguration"
      ],
      "Resource": "arn:aws:lambda:*:*:function:pdf-to-word-converter"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject"
      ],
      "Resource": "arn:aws:s3:::my-pdf-converter-bucket-12345/lambda-deployments/*"
    }
  ]
}
```

---

## Step 3: Local Development & Testing

### 1. Create Virtual Environment
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 2. Run Local Conversion Test
```bash
# Convert a generated sample PDF to Word
python local_test.py

# Convert an existing PDF file
python local_test.py --pdf /path/to/my_document.pdf --out ./my_document.docx
```

### 3. Run Automated Tests
```bash
pytest -v
```

---

## Step 4: Verifying the Deployed Lambda

### Method A: Upload a PDF to S3
1. Go to your S3 bucket `my-pdf-converter-bucket-12345`.
2. Open the `uploads/` folder.
3. Upload any `.pdf` document (e.g. `report.pdf`).
4. Check your Lambda **CloudWatch Logs** (`/aws/lambda/pdf-to-word-converter`).
5. Open the `converted/` folder in your S3 bucket: you will see `report.docx` ready for download!

### Method B: Test in AWS Lambda Console
1. In the AWS Lambda Console, select the **Test** tab.
2. Select **Create new event**.
3. Paste the contents of [`sample_events/s3_event.json`](sample_events/s3_event.json) (replace bucket name and key with your real uploaded file).
4. Click **Test**.
