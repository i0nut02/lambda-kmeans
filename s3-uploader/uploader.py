from flask import Flask, request, jsonify
import boto3
import os
from dotenv import load_dotenv
from flask_cors import CORS

load_dotenv()

s3 = boto3.client(
    "s3",
    region_name=os.getenv("AWS_REGION"),
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
)

BUCKET_NAME = os.getenv("AWS_BUCKET_NAME")
IMG_FOLDER = "../imgs"

def upload_file(file, filename, content_type="image/jpeg"):
    try:
        s3.upload_fileobj(
            file,
            BUCKET_NAME,
            filename,
            ExtraArgs={"ContentType": content_type}
        )
        url = f"https://{BUCKET_NAME}.s3.{os.getenv('AWS_REGION')}.amazonaws.com/{filename}"
        print(f"✅ Uploaded: {filename} -> {url}")
        return True
    except Exception as e:
        print(f"❌ Failed to upload {filename}: {e}")
        return False


def upload_images():
    if not os.path.isdir(IMG_FOLDER):
        print(f"❌ Directory {IMG_FOLDER} does not exist")
        return

    for filename in os.listdir(IMG_FOLDER):
        path = os.path.join(IMG_FOLDER, filename)

        if not os.path.isfile(path):
            continue  # Skip folders or symlinks

        # Infer content type (optional, can use "image/jpeg" for all)
        ext = os.path.splitext(filename)[-1].lower()
        if ext in [".png"]:
            content_type = "image/png"
        elif ext in [".jpg", ".jpeg"]:
            content_type = "image/jpeg"
        else:
            content_type = "application/octet-stream"  # fallback

        with open(path, "rb") as f:
            upload_file(f, filename, content_type)

if __name__ == "__main__":
    upload_images()
