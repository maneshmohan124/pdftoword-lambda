# Serverless PDF to Word (.docx) Converter (Python 3.14 on AWS Lambda)

A serverless application built with **Python 3.14** that automatically converts uploaded PDF documents into editable Word (`.docx`) files.

### Your Configured AWS Environment:
- **Input S3 Bucket**: `qtree-lambda-bucket`
- **Output S3 Bucket**: `qtreeclassreplica`
- **Lambda Function**: `pdftoword`
- **AWS Region**: `us-east-1`

---

## Architecture Flow

```
[ User ]
   │
   ├─► 1. Uploads "sample.pdf" to: s3://qtree-lambda-bucket/sample.pdf
   │
[ qtree-lambda-bucket (S3) ]
   │
   └─► 2. S3 ObjectCreated Event triggers Lambda: "pdftoword" (us-east-1)
          │
     [ AWS Lambda: pdftoword (Python 3.14) ]
          │
          ├─► 3. Downloads PDF to /tmp
          ├─► 4. Converts PDF -> DOCX (using pdf2docx engine with fallback)
          ├─► 5. Uploads "sample.docx" to: s3://qtreeclassreplica/converted/sample.docx
          └─► 6. Cleans up /tmp temporary storage
```

---

## AWS Setup for Your Existing Lambda (`pdftoword`)

Since your Lambda function `pdftoword` is already created in `us-east-1`, verify the following 3 settings in the AWS Console:

### 1. IAM Role Permissions for `pdftoword`
Your Lambda's execution role needs permissions to read from `qtree-lambda-bucket` and write to `qtreeclassreplica`.

Go to **IAM Console** > **Roles** > Select your Lambda role > **Add permissions** > **Create inline policy** (JSON):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ReadFromInputBucket",
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::qtree-lambda-bucket",
        "arn:aws:s3:::qtree-lambda-bucket/*"
      ]
    },
    {
      "Sid": "WriteToOutputBucket",
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::qtreeclassreplica",
        "arn:aws:s3:::qtreeclassreplica/*"
      ]
    }
  ]
}
```

---

### 2. Lambda Configuration Settings
In the AWS Lambda Console for `pdftoword`:

1. **General Configuration**:
   - **Memory**: Set to at least **1024 MB** (recommended for document layout extraction).
   - **Timeout**: Set to **2 minutes (120 sec)**.
   - **Ephemeral storage (`/tmp`)**: **1024 MB**.
2. **Environment Variables**:
   - `OUTPUT_S3_BUCKET` = `qtreeclassreplica`
   - `OUTPUT_PREFIX` = `converted/`
   - `LOG_LEVEL` = `INFO`
   - `AWS_REGION` = `us-east-1`

---

### 3. Add S3 Trigger on `qtree-lambda-bucket`
1. In the AWS Lambda Console for `pdftoword`, click **Add trigger**.
2. Source: **S3**.
3. Bucket: **`qtree-lambda-bucket`**.
4. Event types: `All object create events` (`s3:ObjectCreated:*`).
5. (Optional) Suffix: `.pdf` (only trigger for PDF files).
6. Acknowledge the recursive invocation prompt and click **Add**.

---

## GitHub Actions Automated Deployment

Whenever you push code changes to your repository (`main` branch), GitHub Actions automatically packages the Linux-compatible dependencies and deploys the update to your `pdftoword` Lambda function.

### GitHub Repository Secrets
Go to your GitHub repo > **Settings** > **Secrets and variables** > **Actions** > **New repository secret**:

| Secret Name | Required? | Value |
|---|---|---|
| `AWS_ACCESS_KEY_ID` | **Yes** | Your AWS IAM User Access Key |
| `AWS_SECRET_ACCESS_KEY` | **Yes** | Your AWS IAM User Secret Key |
| `AWS_REGION` | Optional | Defaults to `us-east-1` |
| `LAMBDA_FUNCTION_NAME` | Optional | Defaults to `pdftoword` |
| `DEPLOYMENT_BUCKET` | Optional | Defaults to `qtreeclassreplica` |

---

## Local Development & Testing

### 1. Run Local Conversion Test
```bash
source .venv/bin/activate

# Converts a generated test PDF to Word
python local_test.py

# Convert an existing PDF file
python local_test.py --pdf /path/to/my_file.pdf --out ./my_file.docx
```

### 2. Run Automated Unit Tests
```bash
pytest -v
```

### 3. Test in AWS Lambda Console
In your `pdftoword` Lambda console:
1. Go to the **Test** tab.
2. Select **Create new event**.
3. Paste the contents of [`sample_events/s3_event.json`](sample_events/s3_event.json).
4. Click **Test**.
