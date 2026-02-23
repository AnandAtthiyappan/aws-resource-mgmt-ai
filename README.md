# GenAI Agent AWS Infrastructure Management - Setup Guide

## Overview

This application supports **both Anthropic Claude and Google Gemini** as AI providers. You can switch between them by changing a single environment variable. 

An AI-driven AWS infrastructure management platform that enables you to control and manage cloud resources using natural language conversations. Built with Claude AI, FastAPI, and Streamlit.

## Features

- **Simple Language Interface**: Manage AWS resources using plain English
- **AI-Powered Tool Selection**: Claude/Gemini parses the text & chooses the right AWS operations
- **AWS Integration**: Actually creates and manages AWS resources
- **Intelligent Responses**: Get both technical data and human explanations
- **CloudWatch Monitoring**: Analyse logs and debug Lambda functions
- **Conversational AI**: Context-aware conversations with memory

## Architecture

```
User (Streamlit) → FastAPI → AI Agent (Claude/Gemini) → AWS APIs → Response
```

### Components:
- **Frontend**: Streamlit chat interface
- **Backend**: FastAPI server with CORS
- **AI Agent**: Claude/Gemini with function calling
- **AWS Integration**: Cloud Control API + CloudWatch Logs

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- AWS Account with appropriate permissions
- Anthropic API key / Google Gemini API Key


### 1. Initial setup - repo cloning & Virtual Environment creation

Clone the repo
open command prompt and cd to the specific directory where repo is cloned
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

This installs both `anthropic` and `google-generativeai` packages.

### 3. Environment variable & Choose Your AI Provider

## Complete .env Example

```bash
# Choose your AI provider
AI_PROVIDER=gemini

# Anthropic Claude (if AI_PROVIDER=claude)
ANTHROPIC_API_KEY=your-key-here
ANTHROPIC_MODEL=modelName eg. claude-3-5-sonnet-latest

# Google Gemini (if AI_PROVIDER=gemini)  
GOOGLE_API_KEY=your-key-here
GOOGLE_MODEL=modelName eg. gemini-2.5-flash

# AWS Credentials (always required)
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_DEFAULT_REGION=eu-north-1

# SSL Configuration for Corporate Networks
# WARNING: Only use DISABLE_SSL_VERIFY for testing!
# For production, use SSL_CERT_FILE with your corporate CA certificate
DISABLE_SSL_VERIFY=true

# Optional: AWS Role ARN
# AWS_ROLE_ARN=arn:aws:iam::ACCOUNT:role/ROLE_NAME
```


Edit your `.env` file and set the `AI_PROVIDER` variable:

```bash
# Use Claude (if you have Anthropic API access)
AI_PROVIDER=claude

# OR use Gemini (free tier available)
AI_PROVIDER=gemini
```

### 4. Add the Appropriate API Key

#### Option A: Using Claude
```bash
AI_PROVIDER=claude
ANTHROPIC_API_KEY=your-key-here
```

Get your key from: https://console.anthropic.com/

#### Option B: Using Gemini (Recommended if no Claude access)
```bash
AI_PROVIDER=gemini
GOOGLE_API_KEY=your-key-here
```

Get your key from: https://aistudio.google.com/api-keys

### 5. Test Your Connection

```bash
python test_connection.py
```

Expected output:
```
✅ API Key found: xxxxx...
✅ Gemini API configured
🔄 Testing API call...
✅ API call successful!
```

### 5. Run the Application

```bash
# Start backend
uvicorn main:app --reload --port 8000

# Start frontend (in another terminal)
streamlit run chat.py --server.port 8501
```

on start of frontend, launch the browser & go to `http://localhost:8501`

## Provider Comparison

| Feature | Anthropic Claude | Google Gemini |
|---------|------------------|---------------|
| **Model** | claude-3-5-sonnet-latest | gemini-2.5-flash |
| **Free Tier** | Limited trial credits | ✅ Generous free tier |
| **Function Calling** | ✅ Supported | ✅ Supported |
| **Speed** | Fast | Very Fast |
| **Cost** | Pay per use | Free tier + pay |
| **Setup** | API key required | Google account + API key |

## Switching Providers

To switch between providers, simply change the `AI_PROVIDER` value in your `.env` file:

```bash
# Switch to Gemini
AI_PROVIDER=gemini

# Switch to Claude
AI_PROVIDER=claude
```

Then restart your application. No code changes needed!

### Sample chatbot question & reply from AWS on S3 bucket infrastructure

```
User: Show me all my S3 buckets
🤖 AI Summary: You've got one S3 bucket! Its name is: 
S3 bucket name
Let me know if you'd like to see more details about it or anything else!

User: create new s3 bucket with name 2026-photo-bucket
🤖 AI Summary: Great news! I've successfully created your new S3 bucket.
The bucket is named 2026--photo-bucket and it's now available for you to use.

User: List instances running in AWS EC2
🤖 AI Summary: It looks like I successfully checked for running EC2 instances, but I didn't find any! The AWS Cloud Control API returned a successful response, but the list of resources was empty.

User:list clusters in AWS ECS
🤖 AI Summary: Okay, I looked up the ECS clusters in the eu-north-1 region for you.
I found 1 cluster:
Name: image-resizer-cluster
Status: It's currently ACTIVE.
Services: It has 1 active service defined within it.
Tasks: Interestingly, it currently has 0 running tasks and 0 pending tasks.
Instances: There are also 0 registered instances associated with this cluster.
```

## Troubleshooting

### "ANTHROPIC_API_KEY not found"
- You have `AI_PROVIDER=claude` but no `ANTHROPIC_API_KEY` in .env
- Solution: Add the key or switch to Gemini

### "GOOGLE_API_KEY not found"
- You have `AI_PROVIDER=gemini` but no `GOOGLE_API_KEY` in .env
- Solution: Add the key or switch to Claude

### "Connection error" with Claude
- Corporate firewall may block `api.anthropic.com`
- Solution: Switch to `AI_PROVIDER=gemini` which often works better in corporate networks

### "API_KEY_INVALID" with Gemini
- Your Google API key is incorrect or expired
- Solution: Generate a new key at https://makersuite.google.com/app/apikey

## Getting API Keys

### Google Gemini (Recommended - Free Tier Available)
1. Go to https://makersuite.google.com/app/apikey
2. Sign in with your Google account
3. Click "Create API Key"
4. Copy the key 

### Anthropic Claude
1. Go to https://console.anthropic.com/
2. Sign up or log in
3. Navigate to API Keys section
4. Create a new API key
5. Copy the key

## Benefits of This Architecture

1. **Flexibility**: Switch providers without code changes
2. **Resilience**: If one provider has issues, switch to the other
3. **Cost Optimization**: Use free tier of Gemini for testing, Claude for production
4. **Network Compatibility**: Gemini often works better in restricted networks

## Recommendations

- **For Testing/Development**: Use `AI_PROVIDER=gemini` (free tier)
- **For Production**: Use `AI_PROVIDER=claude` (more reliable for critical workloads)
- **For Corporate Networks**: Try `AI_PROVIDER=gemini` first (better firewall compatibility)