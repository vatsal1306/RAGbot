import os
import time
import uuid

import boto3
import requests
from dotenv import load_dotenv
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()
load_dotenv()

allow_cors = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_cors,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


class Query(BaseModel):
    query: str


ALLOWED_EXTENSIONS = {'.wav'}


def is_allowed_file(filename: str) -> bool:
    """
    Check if the file has an allowed extension.
    """
    _, extension = os.path.splitext(filename)
    return extension.lower() in ALLOWED_EXTENSIONS


client = boto3.client('bedrock-agent-runtime', aws_access_key_id=os.getenv("ACCESS_KEY_ID"),
                      aws_secret_access_key=os.getenv("SECRET_ACCESS_KEY"), region_name="us-east-1")
s3_client = boto3.client('s3', aws_access_key_id=os.getenv("ACCESS_KEY_ID"),
                         aws_secret_access_key=os.getenv("SECRET_ACCESS_KEY"), region_name="us-east-1")
transcribe_client = boto3.client('transcribe', aws_access_key_id=os.getenv("ACCESS_KEY_ID"),
                                 aws_secret_access_key=os.getenv("SECRET_ACCESS_KEY"), region_name="us-east-1")


@app.get("/")
async def root():
    return {"message": "Home page. Nothing to see here."}


@app.get("/ping")
async def ping():
    return {"message": "connection successful"}


@app.post("/search")
async def search(data: Query):
    response = client.retrieve_and_generate(
        input={
            'text': data.query,
        },
        retrieveAndGenerateConfiguration={
            'knowledgeBaseConfiguration': {
                'knowledgeBaseId': 'T2PHPJ9WCS',
                'modelArn': 'arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-5-sonnet-20240620-v1:0',
            },
            'type': 'KNOWLEDGE_BASE'
        },
    )
    if len(response['citations'][0]['retrievedReferences']) == 0:
        return {"text": "Sorry, I am unable to assist you with this request.", "file": "", "page_no": 0}

    file_uri = response['citations'][0]['retrievedReferences'][0]['metadata']['x-amz-bedrock-kb-source-uri']
    page_no = int(
        response['citations'][0]['retrievedReferences'][0]['metadata']['x-amz-bedrock-kb-document-page-number'])
    text = response['output']['text']
    output = {"text": text, "file": os.path.basename(file_uri), "page_no": page_no}
    return output


@app.post("/voice_search")
async def voice_search(audio: UploadFile = File(...)):
    if not is_allowed_file(audio.filename):
        raise HTTPException(status_code=400,
                            detail=f"Invalid file extension. Only .wav file is allowed.")

    unique_id = uuid.uuid4()

    # Save the uploaded audio file
    audio_path = f"tmp/{unique_id}.wav"
    with open(audio_path, "wb") as f:
        f.write(await audio.read())

    # Upload the audio file to an S3 bucket
    bucket_name = 'bobcat-ai'
    s3_key = f"audio/{unique_id}.wav"
    s3_client.upload_file(audio_path, bucket_name, s3_key)

    # Start transcription job
    job_name = f"transcription-job-{unique_id}"
    transcribe_client.start_transcription_job(
        TranscriptionJobName=job_name,
        Media={'MediaFileUri': f's3://{bucket_name}/{s3_key}'},
        MediaFormat='wav',
        LanguageCode='en-US'
    )

    # Wait for the transcription job to complete
    while True:
        status = transcribe_client.get_transcription_job(TranscriptionJobName=job_name)
        if status['TranscriptionJob']['TranscriptionJobStatus'] in ['COMPLETED', 'FAILED']:
            break
        time.sleep(5)

    if status['TranscriptionJob']['TranscriptionJobStatus'] == 'COMPLETED':
        transcript_url = status['TranscriptionJob']['Transcript']['TranscriptFileUri']
        # Fetch the transcript from the URL
        response = requests.get(transcript_url)
        transcript = response.json()['results']['transcripts'][0]['transcript']

        # Use the extracted text to query the existing search functionality
        query_data = Query(query=transcript)
        return await search(query_data)
    else:
        return {"error": "Transcription job failed"}

# if __name__ == "__main__":
#     uvicorn.run('app:app', host='0.0.0.0', port=8001)
