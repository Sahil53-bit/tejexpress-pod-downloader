from flask import Flask, request, jsonify, render_template
import os
import requests
import pandas as pd
import tkinter as tk
from tkinter import filedialog

app = Flask(__name__)

# API Credentials
USERNAME = "TEJEXPRESS122771B2B"
PASSWORD = "Tejexp@2021"

# API Endpoints
LOGIN_URL = "https://ltl-clients-api.delhivery.com/ums/login"
POD_DOWNLOAD_URL = "https://ltl-clients-api.delhivery.com/document/download"

# Ask user for folder location (default to Desktop)
def get_save_folder():
    root = tk.Tk()
    root.withdraw()  # Hide the main window
    folder_selected = filedialog.askdirectory(title="Select Folder to Save PODs")  
    if not folder_selected:
        # Default to Desktop if user cancels
        folder_selected = os.path.join(os.path.expanduser("~"), "Desktop", "POD_Downloads")
    os.makedirs(folder_selected, exist_ok=True)  # Ensure the folder exists
    return folder_selected

# Get folder once at the start
SAVE_FOLDER = get_save_folder()

def get_auth_token():
    """Logs in to get JWT token."""
    payload = {"username": USERNAME, "password": PASSWORD}
    response = requests.post(LOGIN_URL, json=payload)
    if response.status_code == 200 and "data" in response.json():
        return response.json()["data"]["jwt"]
    else:
        return None

def download_pod(lr_number, new_file_name, auth_token):
    """Fetches and downloads the POD to the selected folder."""

    # Check if file already exists
    jpg_path = os.path.join(SAVE_FOLDER, f"{new_file_name}.jpg")
    pdf_path = os.path.join(SAVE_FOLDER, f"{new_file_name}.pdf")

    if os.path.exists(jpg_path) or os.path.exists(pdf_path):
        print(f"✅ Skipping {new_file_name} (Already Downloaded)")
        return None  # Skip if already downloaded

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

            print(f"✅ POD downloaded and saved at: {file_path}")
            return file_path  # Return file path
    except Exception as e:
        print(f"❌ Error fetching POD for LR {lr_number}: {str(e)}")
        return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    """Handles Excel file upload, fetches PODs, and saves them in the selected folder."""
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

        return jsonify({"message": f"PODs downloaded successfully! Check your selected folder: {SAVE_FOLDER}"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
