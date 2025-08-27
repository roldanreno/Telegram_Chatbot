import json
import os
import urllib3
import boto3
from datetime import datetime
from botocore.exceptions import ClientError
import uuid

BOT_TOKEN = os.environ['BOT_TOKEN']
BEDROCK_AGENT_ID = os.environ['AGENT_ID']
BEDROCK_AGENT_ALIAS_ID = os.environ['AGENT_ALIAS_ID']
AWS_REGION = os.environ['REGION']
DYNAMODB_TABLE_NAME = os.environ['DYNAMODB_TABLE_NAME']

# Initialize clients outside handler for connection reuse
bedrock_agent = boto3.client('bedrock-agent-runtime', region_name=AWS_REGION)
dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)
table = dynamodb.Table(DYNAMODB_TABLE_NAME)
http = urllib3.PoolManager()  # Reuse HTTP connections

def store_conversation(session_id, user_message, agent_response, timestamp, user_name=None, chat_id=None):
    """
    Store conversation data in DynamoDB
    """
    try:
        conversation_id = str(uuid.uuid4())
        
        item = {
            'conversation_id': conversation_id,
            'session_id': session_id,
            'timestamp': timestamp,
            'user_message': user_message,
            'agent_response': agent_response,
            'ttl': int((datetime.now().timestamp() + (30 * 24 * 60 * 60)))  # 30 days TTL
        }
        
        # Add optional fields if provided
        if user_name:
            item['user_name'] = user_name
        if chat_id:
            item['chat_id'] = str(chat_id)
            
        table.put_item(Item=item)
        print(f"*** Conversation stored with ID: {conversation_id}")
        
    except ClientError as e:
        print(f"*** Error storing conversation in DynamoDB: {e}")
    except Exception as e:
        print(f"*** Unexpected error storing conversation: {e}")

def call_bedrock_agent(message_text, session_id):
    """
    Call Bedrock agent and return the response
    """
    try:
        print(f"*** Calling Bedrock agent with message: {message_text}")
        
        response = bedrock_agent.invoke_agent(
            agentId=BEDROCK_AGENT_ID,
            agentAliasId=BEDROCK_AGENT_ALIAS_ID,
            sessionId=session_id,
            inputText=message_text
        )
        
        # Extract the response from the event stream
        event_stream = response['completion']
        agent_response = ""
        
        for event in event_stream:
            print(f"*** Event received: {event}")
            if 'chunk' in event:
                chunk = event['chunk']
                if 'bytes' in chunk:
                    chunk_text = chunk['bytes'].decode('utf-8')
                    agent_response += chunk_text
                    print(f"*** Chunk text: {chunk_text}")
        
        # Clean up the response
        agent_response = agent_response.strip()
        
        if not agent_response:
            print("*** Warning: Empty response from Bedrock agent")
            return "🤖 I received your message but couldn't generate a response. Please try again!"
        
        print(f"*** Final Bedrock agent response: {agent_response}")
        return agent_response
        
    except ClientError as e:
        print(f"*** Error calling Bedrock agent: {e}")
        if "AccessDeniedException" in str(e):
            return "🤖 Bot is currently being configured. Please try again in a few minutes!"
        elif "ThrottlingException" in str(e):
            return "🤖 I'm a bit busy right now. Please try again in a moment!"
        else:
            return "🤖 Sorry, I'm having trouble processing your request right now. Please try again later!"
    except Exception as e:
        print(f"*** Unexpected error: {e}")
        return "🤖 Something went wrong. Please try again!"

def sendReply(chat_id, message):
    reply = {
        "chat_id": chat_id,
        "text": message
    }

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    print("URL: " + url)

    encoded_data = json.dumps(reply).encode('utf-8')
    response = http.request('POST', url, body=encoded_data, headers={'Content-Type': 'application/json'})
    
    print(f"*** Reply sent: {encoded_data}")
    print(f"*** Telegram API response status: {response.status}")
    
    return response.status == 200

def lambda_handler(event, context):
    print("*** Received event")
    print(json.dumps(event))
    
    try:
        # Handle both direct test events and API Gateway webhook events
        if 'body' in event:
            # Real webhook from API Gateway
            body = json.loads(event['body'])
        else:
            # Direct test event
            body = event
        
        # Check if this is a valid Telegram update
        if 'message' not in body:
            print("*** No message found in body")
            return {
                'statusCode': 400,
                'body': json.dumps('Invalid webhook data')
            }

        chat_id = body['message']['chat']['id']
        user_name = body['message']['from'].get('username', 'Unknown')
        message_text = body['message']['text']
        user_id = body['message']['from']['id']

        print(f"*** chat id: {chat_id}")
        print(f"*** user name: {user_name}")
        print(f"*** user id: {user_id}")
        print(f"*** message text: {message_text}")

        # Use user_id as session_id for Bedrock agent to maintain conversation context
        session_id = str(user_id)
        timestamp = datetime.now().isoformat()
        
        # Call Bedrock agent instead of simple reply
        agent_response = call_bedrock_agent(message_text, session_id)
        
        # Send the agent's response back to Telegram
        success = sendReply(chat_id, agent_response)
        
        # Only store the conversation if the message was sent successfully AND we got a valid response
        if success and agent_response and not agent_response.startswith("🤖"):
            store_conversation(
                session_id=session_id,
                user_message=message_text,
                agent_response=agent_response,
                timestamp=timestamp,
                user_name=user_name,
                chat_id=chat_id
            )
            print("*** Conversation stored successfully")
        else:
            if not success:
                print("*** Conversation NOT stored - Telegram send failed")
            elif not agent_response or agent_response.startswith("🤖"):
                print("*** Conversation NOT stored - Invalid/Error response from Bedrock")
            else:
                print("*** Conversation NOT stored - Unknown reason")
        
        if success:
            return {
                'statusCode': 200,
                'body': json.dumps('Message processed successfully')
            }
        else:
            return {
                'statusCode': 500,
                'body': json.dumps('Failed to send reply to Telegram')
            }
            
    except Exception as e:
        print(f"*** Error in lambda_handler: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps(f'Error processing message: {str(e)}')
        }