# Use the Converse API to send a text message to Llama 2 Chat 13B.

from botocore.exceptions import ClientError
import boto3


# Create a Bedrock Runtime client in the AWS Region you want to use.
client = boto3.client("bedrock-runtime", region_name="us-east-1")

# Set the model ID, e.g., Titan Text Premier.
model_id = "us.meta.llama3-2-11b-instruct-v1:0"

# Start a conversation with the user message.
user_message = """I have got a red patch on my elbow, it itches very bad, why?"""
conversation = [
    {
        "role": "user",
        "content": [{"text": user_message}],
    }
]

try:
    # Send the message to the model, using a basic inference configuration.
    response = client.converse(
        modelId= model_id,
        messages=conversation,
        inferenceConfig={"maxTokens":512,"temperature":0.5,"topP":0.9},
        additionalModelRequestFields={}
    )

    # Extract and print the response text.
    response_text = response["output"]["message"]["content"][0]["text"]
    print(response_text)

except (ClientError, Exception) as e:
    print(f"ERROR: Can't invoke '{model_id}'. Reason: {e}")
    exit(1)
