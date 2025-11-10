from flask import Flask, request, jsonify
from flask_cors import CORS
import boto3
from botocore.exceptions import ClientError
import logging
import os  # <-- Import the 'os' module

# --- CONFIGURATION ---
# We now get these from Render's 'Environment Variables'
# These will be set in your Render dashboard
UPLOAD_BUCKET_NAME = os.environ.get("UPLOAD_BUCKET_NAME")
DOWNLOAD_BUCKET_NAME = os.environ.get("DOWNLOAD_BUCKET_NAME")
FRONTEND_URL = os.environ.get("FRONTEND_URL") # Your GitHub Pages URL

app = Flask(__name__)

# --- SECURE CORS ---
# This is CRITICAL. It only allows requests from your specific GitHub Pages site.
if FRONTEND_URL:
    CORS(app, resources={
        r"/generate-upload-url": {"origins": [FRONTEND_URL]}
    })
else:
    # Fallback for local testing if you want
    CORS(app) 

# --- Boto3 Client ---
# Load credentials from Environment Variables set in Render
s3_client = boto3.client(
    "s3",
    aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
    region_name=os.environ.get('AWS_DEFAULT_REGION')
)

@app.route("/generate-upload-url", methods=["GET"])
def generate_upload_url():
    file_name = request.args.get("filename")
    if not file_name:
        return jsonify({"error": "filename query parameter is required"}), 400

    print(f"Generating URLs for: {file_name}")

    try:
        # 1. Generate the UPLOAD URL (PUT)
        upload_url = s3_client.generate_presigned_url(
            ClientMethod="put_object",
            Params={"Bucket": UPLOAD_BUCKET_NAME, "Key": file_name},
            ExpiresIn=200  # Valid for 1 hour
        )
        
        # 2. Generate the DOWNLOAD URL (GET)
        download_url = s3_client.generate_presigned_url(
            ClientMethod="get_object",                               
            Params={"Bucket": DOWNLOAD_BUCKET_NAME, "Key": file_name},
            ExpiresIn=100  # Valid for 20 seconds
        )

        return jsonify({
            "upload_url": upload_url,
            "download_url": download_url
        })
    
    except ClientError as e:
        logging.error(e)
        return jsonify({"error": "Couldn't generate URLs"}), 500

# This is the start command for Gunicorn (what Render uses)
# The "if __name__" block is no longer the main way it starts.
if __name__ == "__main__":
    app.run(port=5000, debug=True)