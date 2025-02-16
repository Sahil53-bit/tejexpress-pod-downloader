from flask import Flask, request, jsonify, send_file, render_template
import requests
import pandas as pd
import os
import shutil
import uuid

# Flask App
app = Flask(__name__)

# API Credentials
USERNAME = "TEJEXPRESS122771B2B"
PASSWORD = "Tejexp@2021"

# API Endpoints
LOGIN_URL = "https://ltl-clients-api.delhivery.com/ums/login"
POD_DOWNLOAD_URL = "https://ltl-clients-api.delhivery.com/document/download"

# Folder for storing PODs
SAVE_FOLDER = "POD_Documents"
os.makedirs(SAVE_FOLDER, exist_ok=True)

def get_auth_token():
    """Logs in to get JWT token."""
    payload = {"username": USERNAME, "password": PASSWORD}
    response = requests.post(LOGIN_URL, json=payload)
    if response.status_code == 200 and "data" in response.json():
        return response.json()["data"]["jwt"]
    else:
        return None

def pod_already_downloaded(new_file_name):
    """Checks if the POD file already exists."""
    jpg_path = os.path.join(SAVE_FOLDER, f"{new_file_name}.jpg")
    pdf_path = os.path.join(SAVE_FOLDER, f"{new_file_name}.pdf")
    return os.path.exists(jpg_path) or os.path.exists(pdf_path)

def download_pod(lr_number, new_file_name, auth_token):
    """Fetches and downloads the POD if not already downloaded."""
    if pod_already_downloaded(new_file_name):
        print(f"✅ Skipping {new_file_name} (Already Downloaded)")
        return None  # Skip download if file exists

    headers = {"Authorization": f"Bearer {auth_token}"}
    params = {"lrn": lr_number, "doc_type": "LM_POD"}
    
    response = requests.get(POD_DOWNLOAD_URL, headers=headers, params=params)
    try:
        json_response = response.json()
        if "data" in json_response and "files" in json_response["data"] and json_response["data"]["files"]:
            pod_url = json_response["data"]["files"][0]["url"]
            file_extension = ".jpg" if "jpg" in pod_url else ".pdf"
            file_path = os.path.join(SAVE_FOLDER, f"{new_file_name}{file_extension}")

            # Download file
            pod_response = requests.get(pod_url)
            with open(file_path, "wb") as file:
                file.write(pod_response.content)

            print(f"✅ POD downloaded and saved as: {file_path}")
            return file_path  # Return file path
    except Exception as e:
        print(f"❌ Error fetching POD for LR {lr_number}: {str(e)}")
        return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    """Handles Excel file upload, fetches PODs, and returns ZIP file."""
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    # Save the uploaded Excel file
    file_path = os.path.join("uploads", file.filename)
    os.makedirs("uploads", exist_ok=True)
    file.save(file_path)

    try:
        df = pd.read_excel(file_path)
        if "LRN" not in df.columns or "New_File_Name" not in df.columns:
            return jsonify({"error": "Excel file must contain 'LRN' and 'New_File_Name' columns"}), 400

        auth_token = get_auth_token()
        if not auth_token:
            return jsonify({"error": "Authentication failed"}), 401

        # Download all missing PODs
        file_paths = []
        for _, row in df.iterrows():
            lr_number = str(row["LRN"])
            new_file_name = str(row["New_File_Name"])
            pod_path = download_pod(lr_number, new_file_name, auth_token)
            if pod_path:
                file_paths.append(pod_path)

        return jsonify({"message": "Process complete!"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
