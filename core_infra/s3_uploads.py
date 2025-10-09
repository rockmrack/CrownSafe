"""
S3 upload helper utilities
Generates region-correct presigned POST URLs for client-side uploads
"""

import os
import boto3
from botocore.config import Config
from typing import Dict, Optional


# Bucket configuration
BUCKET = os.getenv("S3_UPLOAD_BUCKET") or os.getenv("S3_BUCKET", "babyshield-images")
CFG_REGION = os.getenv("S3_UPLOAD_BUCKET_REGION") or os.getenv(
    "S3_BUCKET_REGION", "us-east-1"
)  # Fixed: S3 bucket is in us-east-1


def _bucket_region() -> str:
    """Resolve the bucket's actual region.

    Uses S3 get_bucket_location when region is not explicitly configured.
    """
    if CFG_REGION:
        return CFG_REGION

    try:
        # get_bucket_location must be called against a global endpoint
        s3_global = boto3.client("s3", region_name="us-east-1")
        loc = s3_global.get_bucket_location(Bucket=BUCKET).get("LocationConstraint")
        # Some regions return None for us-east-1
        return loc or "us-east-1"
    except Exception:
        # If we can't determine, use eu-north-1 as default
        return "eu-north-1"


def presign_post(key: str, user_id: int, job_id: str, content_type: str = "image/jpeg") -> Dict:
    """Generate a presigned POST for uploading to S3 with correct regional endpoint.

    Args:
        key: Object key to upload
        user_id: Numeric user id (stored as metadata)
        job_id: The visual job id (stored as metadata)

    Returns:
        A dict with url and fields suitable for HTML form upload
    """
    region = _bucket_region()
    s3 = boto3.client("s3", region_name=region, config=Config(signature_version="s3v4"))

    base_fields = {
        "Content-Type": content_type,
        "x-amz-meta-user-id": str(user_id),
        "x-amz-meta-job-id": job_id,
    }
    conditions = [
        {"Content-Type": content_type},
        ["content-length-range", 1024, 50 * 1024 * 1024],  # 1KB .. 50MB
        {"x-amz-meta-user-id": str(user_id)},
        {"x-amz-meta-job-id": job_id},
        ["starts-with", "$key", f"uploads/{user_id}/"],
    ]

    presigned = s3.generate_presigned_post(
        Bucket=BUCKET,
        Key=key,
        Fields=base_fields,
        Conditions=conditions,
        ExpiresIn=900,
    )

    # Merge so AWS-provided fields (algorithm, credential, date, policy, signature) win
    fields = {**base_fields, **presigned["fields"]}

    # Virtual-hosted-style URL for the region
    if region == "us-east-1":
        url = f"https://{BUCKET}.s3.amazonaws.com"
    else:
        url = f"https://{BUCKET}.s3.{region}.amazonaws.com"

    return {
        "url": url,
        "fields": fields,
        "key": key,
        "region": region,
        "bucket": BUCKET,
    }


def presign_get(
    key: str,
    expires: Optional[int] = None,
    filename: Optional[str] = None,
    content_type: str = "application/pdf",
) -> Dict:
    """Generate a presigned GET URL with filename and content type.

    TTL defaults to PRESIGN_TTL_SECONDS env or 600s.
    """
    region = _bucket_region()
    s3 = boto3.client("s3", region_name=region, config=Config(signature_version="s3v4"))
    ttl = int(os.getenv("PRESIGN_TTL_SECONDS", "600")) if (expires is None) else int(expires)
    params = {"Bucket": BUCKET, "Key": key}
    if filename:
        params["ResponseContentType"] = content_type
        params["ResponseContentDisposition"] = f'attachment; filename="{filename}"'
    url = s3.generate_presigned_url(
        ClientMethod="get_object",
        Params=params,
        ExpiresIn=ttl,
    )
    return {"url": url, "bucket": BUCKET, "region": region, "key": key, "expires_in": ttl}


def upload_file(file_path: str, key: str, content_type: str = "application/pdf") -> Dict:
    """Upload a local file to S3 at the given key.

    Returns dict with bucket, key, region.
    """
    region = _bucket_region()
    s3 = boto3.client("s3", region_name=region, config=Config(signature_version="s3v4"))
    extra_args = {"ContentType": content_type}
    kms_key_id = os.getenv("S3_KMS_KEY_ID")
    if kms_key_id:
        extra_args["ServerSideEncryption"] = "aws:kms"
        extra_args["SSEKMSKeyId"] = kms_key_id
    s3.upload_file(Filename=file_path, Bucket=BUCKET, Key=key, ExtraArgs=extra_args)
    return {"bucket": BUCKET, "key": key, "region": region}
