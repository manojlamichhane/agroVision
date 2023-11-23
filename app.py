import logging
import boto3
from botocore.exceptions import ClientError
import os
from pydantic import BaseModel
import base64
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from typing import Union
from fastapi import FastAPI, File, UploadFile
import tempfile
import hashlib
from boto3.dynamodb.conditions import Key
from fastapi.middleware.cors import CORSMiddleware
import math
import io

load_dotenv()
app = FastAPI()
fileDict = {}
fileString = {}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

s3_client = boto3.client('s3',aws_access_key_id=os.getenv("ACCESS_KEY"),aws_secret_access_key=os.getenv("SECRET_KEY"))
client = boto3.client('rekognition',aws_access_key_id=os.getenv("ACCESS_KEY"),aws_secret_access_key=os.getenv("SECRET_KEY"),region_name=os.getenv("REGION"))

# connect to dynamodb and create a table
dynamo_client = boto3.resource('dynamodb',aws_access_key_id=os.getenv("ACCESS_KEY"),aws_secret_access_key=os.getenv("SECRET_KEY"),region_name=os.getenv("REGION"))

@app.post("/uploadfile",status_code=201)
async def create_upload_file(file: UploadFile = File(...)):
    if file :
        fileDict['fileName'] = file.filename

        # reading the file
        contents = await file.read()
        file.file.seek(0)
        
        # encoding the image to save in the database for caching purpose
        encoded_image = hashlib.sha256(contents).hexdigest()
        
        fileString[file.filename] = encoded_image
        
        s3_client.upload_fileobj(file.file, os.getenv("BUCKET"), file.filename)

        return {"message" : "File uploaded successfully"}   
    else:
        return {"message": "You're missing one of the following: app_secret, key_id"}

@app.get('/label',status_code=200)
def show_custom_labels():

    table = dynamo_client.Table('ImageResponse')

    # look for the response saved in dynamodb
    responseFromDB = table.query(KeyConditionExpression=Key('image_string').eq(fileString[fileDict['fileName']]))

    if(len(responseFromDB['Items'])>0):
        return {"data":responseFromDB["Items"],"location":"cache"}
    else:    
        if bool(fileDict) :

            responseFromCloud = client.detect_custom_labels(ProjectVersionArn='arn:aws:rekognition:eu-west-1:088594801781:project/NewPlantDetection/version/NewPlantDetection.2023-10-20T16.49.57/1697835000049',
                Image={"S3Object": {"Bucket": os.getenv("BUCKET"), "Name": fileDict['fileName']}}, MinConfidence=85,
            )
            
            # store the response to the dynamodb
            table.put_item(
                Item={
                    'image_string': fileString[fileDict['fileName']],
                    'Name': responseFromCloud['CustomLabels'][0]["Name"],
                    'Confidence': math.trunc(responseFromCloud['CustomLabels'][0]['Confidence'])
                }
            )

            return {"data":responseFromCloud['CustomLabels'],"location":"cloud"}
        else:
            return {'message':'Make sure you upload the image first'}