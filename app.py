import logging
import boto3
from botocore.exceptions import ClientError
import os

from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from typing import Union
from fastapi import FastAPI

load_dotenv()

app = FastAPI()

fileDict = {}

@app.get("/")
def index():
    return 'Hello world'

@app.post('/upload-file')    
def upload_file( ):

    if 'upload_file' in request.files.keys() :
        
        file_upload =  request.files['upload_file']
        print(file_upload.filename)
        fileDict['fileName'] = file_upload.filename

        file_upload.save(secure_filename(file_upload.filename))

        # Upload the file

        s3_client = boto3.client('s3',aws_access_key_id=os.getenv("ACCESS_KEY"),aws_secret_access_key=os.getenv("SECRET_KEY"))
    
        s3_client.upload_file(file_upload.filename, os.getenv("BUCKET"), file_upload.filename)

        return jsonify({"Status" : "File uploaded successfully"})   
    else:
        return jsonify({"error": "You're missing one of the following: app_secret, key_id"})

@app.get('/get-label')
def show_custom_labels():

    if bool(fileDict) :

        client=boto3.client('rekognition',aws_access_key_id=os.getenv("ACCESS_KEY"),aws_secret_access_key=os.getenv("SECRET_KEY"),region_name=os.getenv("REGION"))

        response = client.detect_custom_labels(ProjectVersionArn='arn:aws:rekognition:eu-west-1:088594801781:project/NewPlantDetection/version/NewPlantDetection.2023-10-20T16.49.57/1697835000049',
            Image={"S3Object": {"Bucket": os.getenv("BUCKET"), "Name": fileDict['fileName']}}, MinConfidence=95,
        )

        return jsonify({"data":response['CustomLabels']})
    else:
        return jsonify({'error':'Make sure you upload the image first'})