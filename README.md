# Telegram Reno Gaming Bot CDK

TypeScript CDK project for deploying the Telegram gaming assistant bot with Bedrock AI.

## Architecture
- **Lambda**: telegram-reno-bot (Python 3.13, ARM64)
- **DynamoDB**: telegram-bedrock-conversations with GSI
- **API Gateway**: REST API with /webhook endpoint
- **Bedrock Agent**: "Reno Gaming Assistant" with Claude 3.7 Sonnet
- **IAM**: Roles and policies for all services

## Features
- **Gaming Content Creator Assistant**: Specialized AI for gaming strategies, content creation, and skill improvement
- **Multilingual Support**: Responds in user's language
- **Conversation History**: Persistent storage in DynamoDB
- **Serverless Architecture**: Cost-effective, auto-scaling infrastructure

## Setup

1. Install dependencies:
```bash
npm install
```

2. Deploy:
```bash
cdk bootstrap
cdk deploy
```

3. Enable Bedrock model access:
   - Go to AWS Bedrock console
   - Navigate to Model access
   - Request access to Claude 3.7 Sonnet model
   - Wait for approval (usually instant)

4. Update Bedrock agent model (if needed):
   - Go to AWS Bedrock console → Agents
   - Select "Reno-Gaming-Assistant" agent
   - Click "Edit" → "Agent builder"
   - Update "Foundation model" to desired Claude version
   - Click "Save and exit"
   - Click "Prepare" and wait for completion
   - Go to "Aliases" tab → Select "TSTALIASID"
   - Click "Update alias" → "Create new version"
   - Select the latest agent version
   - Click "Update alias"

5. Configure Telegram bot:
   - Create bot with @BotFather
   - Update `BOT_TOKEN` in Lambda environment variables
   - Set webhook URL: `https://your-api-gateway-url/webhook`

## Environment Variables
Auto-configured in CDK:
- `BOT_TOKEN`: `<telegram_bot_token>` (update after deployment)
- `AGENT_ID`: Auto-generated from Bedrock agent
- `AGENT_ALIAS_ID`: Auto-generated from agent alias
- `REGION`: `us-east-1`
- `DYNAMODB_TABLE_NAME`: `telegram-bedrock-conversations`

## Bedrock Agent
**Name**: Reno Gaming Assistant  
**Model**: Claude 3.7 Sonnet  
**Capabilities**: Strategy guides, content creation, skill assessment, meta analysis, creator guidance