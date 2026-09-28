# CloudBase Cloud Functions (Serverless) Entry Point
# Use this if you prefer Cloud Functions over container deployment
# Note: Cloud Functions have a 3-second timeout on free tier

import json
from mangum import Mangum
from app.main import app

# Wrap FastAPI app for AWS Lambda / CloudBase compatibility
handler = Mangum(app, lifespan="off")


def main_handler(event, context):
    """
    CloudBase Cloud Function handler.
    Supports both HTTP trigger and API Gateway trigger.
    """
    # CloudBase wraps the event differently depending on trigger type
    if "httpMethod" in event:
        # API Gateway / HTTP trigger
        return handler(event, context)
    else:
        # Direct invoke
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"message": "Football Assistant API is running"})
        }
