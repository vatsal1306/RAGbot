import os

import boto3
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()
load_dotenv()


class Query(BaseModel):
    query: str


@app.get("/")
async def root():
    return {"message": "Home page. Nothing to see here."}


@app.post("/search")
async def search(data: Query):
    client = boto3.client('bedrock-agent-runtime', aws_access_key_id=os.getenv("ACCESS_KEY_ID"),
                          aws_secret_access_key=os.getenv("SECRET_ACCESS_KEY"), region_name="us-east-1")
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
    return response['output']['text']
