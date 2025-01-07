from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
import os
from botocore.exceptions import ClientError
from dotenv import load_dotenv
import boto3
import base64
import json
from werkzeug.security import check_password_hash, generate_password_hash
from database.database_models import add_generated_content, add_new_user
import uuid
from datetime import datetime
from werkzeug.utils import secure_filename
from botocore.config import Config

load_dotenv()
application = Flask(__name__)
application.secret_key = os.getenv('SECRET_KEY')
dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
users_table = dynamodb.Table('Users')
generated_content_table = dynamodb.Table('GeneratedContent')

boto_config = Config(
    region_name=os.environ.get('AWS_REGION', 'us-east-1'),
    retries = {'max_attempts': 3}
)

sagemaker_runtime = boto3.client(
    "sagemaker-runtime",
    config=boto_config
)

# sagemaker_runtime = boto3.client("sagemaker-runtime", region_name="us-east-1")
endpoint_name = "blogify-endpoint-v1"

def invoke_sagemaker_endpoint(payload):
    try:
        response = sagemaker_runtime.invoke_endpoint(
            EndpointName=endpoint_name,
            Body=json.dumps(payload),
            ContentType="application/json"
        )
        response_body = json.loads(response["Body"].read())
        return response_body
    except (ClientError, Exception) as e:
        print(f"Error invoking endpoint: {e}")
        return None
    
@application.route('/process_payload', methods=['POST'])
def process_payload():
    try:
       
        data = request.get_json()
        mode = data.get("mode", "text2img")
        lora = data.get("lora", "No LoRA")
        prompt = data.get("prompt", "")
        negative_prompt = data.get("negative_prompt", "")
        num_inference_steps = int(data.get("num_inference_steps", 50))
        guidance_scale = float(data.get("guidance_scale", 7.5))
        height = int(data.get("height", 512))
        width = int(data.get("width", 512))
        seed = int(data.get("seed", 42))

        # Prepare payload for SageMaker
        payload = {
            "mode": mode,
            "lora": lora,
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "num_inference_steps": num_inference_steps,
            "guidance_scale": guidance_scale,
            "height": height,
            "width": width,
            "seed": seed
        }

        # Invoke SageMaker endpoint
        response = invoke_sagemaker_endpoint(payload)

        if response and "image" in response:
            return jsonify({"image": response["image"], "message": "Image generated successfully."})
        else:
            return jsonify({"message": "Image generation failed."}), 500
    except Exception as e:
        print(f"Error processing payload: {e}")
        return jsonify({"message": "An error occurred while processing the payload."}), 500
 
# @application.route('/', methods=['GET', 'POST'])
# def login():
#     if request.method == 'POST':
#         username = request.form['username']
#         password = request.form['password']
#         try:
#             response = users_table.scan(
#                 FilterExpression='Username = :username',
#                 ExpressionAttributeValues={':username': username}
#             )
#             items = response.get('Items')

#             if items:
#                 user = items[0]  
#                 if check_password_hash(user['PasswordHash'], password):
#                     session['user_id'] = user['UserID']
#                     session['username'] = user['Username']
#                     flash('Login successful!', 'success')
#                     return redirect(url_for('index'))
#                 else:
#                     flash('Invalid password. Please try again.', 'danger')
#             else:
#                 flash('User not found. Please register.', 'warning')
#                 return redirect(url_for('register'))
#         except Exception as e:
#             print(f"Error querying DynamoDB: {e}")
#             flash('An error occurred. Please try again later.', 'danger')

#     return render_template('login.html')

# @application.route('/register', methods=['GET', 'POST'])
# def register():
#     if request.method == 'POST':
#         username = request.form['username']
#         password = request.form['password']
#         email = request.form['email']
#         try:
#             response = users_table.scan(
#                 FilterExpression='Username = :username',
#                 ExpressionAttributeValues={':username': username}
#             )
#             if response['Items']:
#                 flash('Username already exists. Please choose a different one.', 'danger')
#                 return redirect(url_for('register'))
#         except Exception as e:
#             print(f"Error querying DynamoDB: {e}")
#             flash('An error occurred. Please try again later.', 'danger')
#             return redirect(url_for('register'))


#         user_id = str(uuid.uuid4())
#         password_hash = generate_password_hash(password)


#         try:
#             user_item = {
#                 'UserID': user_id,
#                 'Username': username,
#                 'PasswordHash': password_hash,
#                 'Email': email,
#                 'Timestamp': str(datetime.utcnow())
#             }
#             users_table.put_item(Item=user_item)
#             flash('Registration successful! You can now log in.', 'success')
#             return redirect(url_for('login'))
#         except Exception as e:
#             print(f"Error adding user to DynamoDB: {e}")
#             flash('An error occurred. Please try again later.', 'danger')

#     return render_template('register.html')


def get_sdxl_image(prompt):
    client = boto3.client("bedrock-runtime", region_name="us-east-1")
    model_id = "stability.stable-diffusion-xl-v1"
    native_request = {"text_prompts":[{"text": prompt,"weight":1}],"cfg_scale":10,"steps":50,"seed":0,"width":1024,"height":1024,"samples":1}
    request = json.dumps(native_request)
    response = client.invoke_model(modelId=model_id, body=request)
    model_response = json.loads(response["body"].read())
    base64_image_data = model_response["artifacts"][0]["base64"]
    try:
        request_payload = json.dumps(native_request)
        response = client.invoke_model(modelId=model_id, body=request_payload)
        model_response = json.loads(response["body"].read())
        base64_image_data = model_response["artifacts"][0]["base64"]
        
        return base64_image_data
    except (ClientError, Exception) as e:
        print(f"ERROR: Can't invoke '{model_id}'. Reason: {e}")
        return None


def get_llma_response(topic, number_of_words, blog_type ):
    client = boto3.client("bedrock-runtime", region_name="us-east-1")
    model_id = "us.meta.llama3-2-11b-instruct-v1:0"
    prompt = f"Write a blog about '{topic}' aimed at {blog_type} in about {number_of_words} words."
    conversation = [
        {
            "role": "user",
            "content": [{"text": prompt}],
        }
    ]

    try:
        response = client.converse(
            modelId= model_id,
            messages=conversation,
            inferenceConfig={"maxTokens":512,"temperature":0.5,"topP":0.9},
            additionalModelRequestFields={}
        )

        response_text = response["output"]["message"]["content"][0]["text"]
        print(response_text)
        return response_text
    except (ClientError, Exception) as e:
        print(f"ERROR: Can't invoke '{model_id}'. Reason: {e}")
        exit(1)
def get_llma_img_prompt(generate_blog,topic,blog_type):
    client = boto3.client("bedrock-runtime", region_name="us-east-1")
    model_id = "us.meta.llama3-2-11b-instruct-v1:0"
    # prompt = f"Write a sentence for the image generation model based on the blog post '{generate_blog}', topic of '{topic}' and aimed at '{blog_type}'"
    prompt = f"Generate a descriptive and vivid prompt for a Stable Diffusion image model based on the blog post '{generate_blog}', with a focus on the topic '{topic}', and aimed at a '{blog_type}' audience. The prompt should include specific visual details, mood, colors, and any key elements or symbols that represent the main themes of the topic to help the model generate an engaging and relevant image of 20 words."

    conversation = [
        {
            "role": "user",
            "content": [{"text": prompt}],
        }
    ]

    try:
        response = client.converse(
            modelId= model_id,
            messages=conversation,
            inferenceConfig={"maxTokens":512,"temperature":0.5,"topP":0.9},
            additionalModelRequestFields={}
        )
        response_text = response["output"]["message"]["content"][0]["text"]
        print(response_text)
        return response_text
    except (ClientError, Exception) as e:
        print(f"ERROR: Can't invoke '{model_id}'. Reason: {e}")
        exit(1)



@application.route('/submit_blog', methods=['POST'])
def handle_submit():

    if request.method == 'POST':
        topic = request.form['input_text']
        number_of_words = request.form['no_words']
        blog_type = request.form['blog_style']

        generate_blog = get_llma_response(topic, number_of_words, blog_type)
        generate_image_prompt = get_llma_img_prompt(generate_blog,topic,blog_type)

        base64_image_data = get_sdxl_image(generate_image_prompt)
        if base64_image_data:
            
            return jsonify({'base64_image': base64_image_data,'generated_blog': generate_blog, 'image_prompt':generate_image_prompt})
        else:
            return jsonify({'error': 'Image generation failed'}), 500
        # add_generated_content(prompt=topic, content=generate_blog, user_id=session['user_id'])
           
@application.route('/generate_image', methods=['POST'])
def generate_image():
    if request.method == 'POST':
        prompt = request.form['image_prompt']
        

@application.route("/")
def index():
    return render_template("index.html")
# @application.route('/index')
# def index():
#     if 'username' in session:
#         return render_template('index.html', username=session['username'])
#     else:
#         flash('Please log in to access the home page.', 'info')
#         return redirect(url_for('login'))

@application.route('/logout', methods=['POST'])
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))
    
if __name__ == "__main__":
    application.run(host="0.0.0.0", port=5000, debug=True)