from flask import Flask, request, jsonify
from flask_cors import CORS
import boto3
from botocore.exceptions import ClientError
import logging
import os

# --- CONFIGURATION ---
UPLOAD_BUCKET_NAME = os.environ.get("UPLOAD_BUCKET_NAME")
DOWNLOAD_BUCKET_NAME = os.environ.get("DOWNLOAD_BUCKET_NAME")
FRONTEND_URL = os.environ.get("FRONTEND_URL")

app = Flask(__name__)

# --- SECURE CORS ---
# + We add the new endpoint to the list of allowed resources
if FRONTEND_URL:
    CORS(app, resources={
        r"/generate-upload-url": {"origins": [FRONTEND_URL]},
        r"/check-download-url": {"origins": [FRONTEND_URL]} # + Add new route
    })
else:
    CORS(app) 

# --- Boto3 Client ---
s3_client = boto3.client(
    "s3",
    aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
    region_name=os.environ.get('AWS_DEFAULT_REGION')
)

@app.route("/generate-upload-url", methods=["GET"])
def generate_upload_url():
    """
    Generates a presigned URL for uploading a file.
    """
    file_name = request.args.get("filename")
    if not file_name:
        return jsonify({"error": "filename query parameter is required"}), 400

    print(f"Generating UPLOAD URL for: {file_name}")

    try:
        # - We only generate the UPLOAD URL now
        upload_url = s3_client.generate_presigned_url(
            ClientMethod="put_object",
            Params={"Bucket": UPLOAD_BUCKET_NAME, "Key": file_name},
            ExpiresIn=100  # 1 hour
        )
        
        return jsonify({
            "upload_url": upload_url
        })
    
    except ClientError as e:
        logging.error(e)
        return jsonify({"error": "Couldn't generate upload URL"}), 500

# +++ NEW ENDPOINT FOR POLLING +++
@app.route("/check-download-url", methods=["GET"])
def check_download_url():
    """
    Checks if the file exists in the download bucket.
    If yes, returns a presigned URL. If not, returns 'processing'.
    """
    file_name = request.args.get("filename")
    if not file_name:
        return jsonify({"error": "filename query parameter is required"}), 400

    try:
        # 1. Check if the file exists using head_object
        # This is a lightweight call that only gets metadata, not the file.
        s3_client.head_object(Bucket=DOWNLOAD_BUCKET_NAME, Key=file_name)
        
        # 2. If it exists, generate the download URL
        print(f"File found: {file_name}. Generating download URL.")
        download_url = s3_client.generate_presigned_url(
            ClientMethod="get_object",                               
            Params={"Bucket": DOWNLOAD_BUCKET_NAME, "Key": file_name},
            ExpiresIn=60  # 5 minutes
        )
        
        return jsonify({
            "status": "ready",
            "download_url": download_url
        })

    except ClientError as e:
        # 3. If we get a "404 Not Found" error, it means the file is not ready
        if e.response['Error']['Code'] == '404':
            print(f"File not ready yet: {file_name}")
            return jsonify({"status": "processing"})
        
        # 4. Handle other potential errors
        logging.error(e)
        return jsonify({"error": "Error checking file status"}), 500

if __name__ == "__main__":
    app.run(port=5000, debug=True)