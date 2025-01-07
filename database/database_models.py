# for database features
import boto3
import uuid
from datetime import datetime

dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
users_table = dynamodb.Table('Users')
generated_content_table = dynamodb.Table('GeneratedContent')
def add_new_user(username, password_hash, email):
    user_id = str(uuid.uuid4())  # Generate a unique UserID

    try:
        # Create a new user item
        user_item = {
            'UserID': user_id,
            'Username': username,
            'PasswordHash': password_hash,
            'Email': email,
            'Timestamp': str(datetime.utcnow())  # Current timestamp
        }

        # Insert the item into the Users table
        response = users_table.put_item(Item=user_item)
        print("User added successfully:", response)
    except Exception as e:
        print(f"Error adding new user: {e}")
def add_generated_content(prompt, content, user_id):
    content_id = str(uuid.uuid4())  # Generate a unique ContentID

    try:
        # Create a new content item
        content_item = {
            'ContentID': content_id,
            'Prompt': prompt,
            'Content': content,
            'UserID': user_id,
            'Timestamp': str(datetime.utcnow())  # Current timestamp
        }

        # Insert the item into the GeneratedContent table
        response = generated_content_table.put_item(Item=content_item)
        print("Content added successfully:", response)
    except Exception as e:
        print(f"Error adding content: {e}")

# add_new_user('new_user', 'hashed_password_here', 'user@example.com')
# add_generated_content('Example prompt', 'Generated content here', '08e120d9-8b5b-48c9-9e48-fff4f0b67333')