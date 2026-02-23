# High-Level Design: Data Flow & Control Flow

## Overview

This document describes how a user request flows through the GenAI Agent AWS Infrastructure Management system, from the Streamlit chat interface to AWS resource operations.

## Architecture Diagram

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Streamlit  │────▶│   FastAPI    │────▶│   AI Agent   │────▶│     AWS      │
│   (chat.py)  │◀────│  (main.py)   │◀────│(aws_agent.py)│◀────│  Cloud APIs  │
└──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
     User UI           HTTP Server         Claude/Gemini        Cloud Control
```

## Detailed Control Flow

### Step 1: User Input (Streamlit - chat.py)

User types a natural language request:
```
"Create an S3 bucket named my-photos"
```

**File:** `chat.py:17-23`
```python
user_input = st.chat_input("Say something...")
if user_input:
    st.session_state["messages"].append({"role": "user", "content": user_input})
```

---

### Step 2: HTTP POST to FastAPI (chat.py → main.py)

Streamlit sends the message to the FastAPI backend:

**File:** `chat.py:29-34`
```python
response = requests.post(
    "http://localhost:8000/chat",
    json={
        "message": user_input,
        "history": st.session_state["messages"]
    }
)
```

---

### Step 3: FastAPI Endpoint (main.py)

FastAPI receives the request and delegates to the processor:

**File:** `main.py`
```python
@app.post("/chat")
async def chat(request: Request):
    data = await request.json()
    user_input = data.get("message", "")
    history = data.get("history", [])
    response = process_request(user_input, history)
    return {"response": response, "updated_history": history}
```

---

### Step 4: Processor Bridge (processor.py)

Instantiates the AI agent and forwards the request:

**File:** `processor.py`
```python
def process_request(user_message: str, history: List[Dict]) -> str:
    agent = AWSAgenticAgent()
    return agent.process_request(user_message, history=history)
```

---

### Step 5: AWS Agent Initialization (aws_agent.py)

Agent initializes based on configured AI provider:

**File:** `aws_agent.py:11-27`
```python
class AWSAgenticAgent:
    def __init__(self):
        self.ai_provider = os.getenv('AI_PROVIDER', 'claude').lower()
        
        if self.ai_provider == 'gemini':
            self._init_gemini()
        elif self.ai_provider == 'claude':
            self._init_claude()
        
        self.aws_config = AWSConfig()
        self._test_aws_connection()
```

---

### Step 6: Process Request with AI (aws_agent.py)

Sends user message + tool definitions to AI model:

```python
def process_request(self, user_input: str, history: List[Dict]) -> str:
    if self.ai_provider == 'claude':
        return self._process_request_claude(user_input, history)
    elif self.ai_provider == 'gemini':
        return self._process_request_gemini(user_input, history)
```

**What happens:**
1. Loads tool definitions from `tools.json`
2. Formats tools for the specific AI provider
3. Sends user message + tools + history to AI
4. AI decides: return text OR call a function

---

### Step 7: AI Returns Function Call

If the AI determines an AWS operation is needed, it returns a structured function call:

```json
{
  "name": "aws_cloud_control",
  "args": {
    "operation": "create",
    "resource_type": "AWS::S3::Bucket",
    "properties": {"BucketName": "my-photos"},
    "region": "eu-north-1"
  }
}
```

---

### Step 8: Execute AWS Operation (aws_agent.py)

The agent executes the AWS operation via Cloud Control API:

**File:** `aws_agent.py - _execute_aws_operation()`

```python
def _execute_aws_operation(self, operation, resource_type, 
                          identifier=None, properties=None, region="eu-north-1"):
    session = self.aws_config.get_session()
    cloudcontrol = session.client('cloudcontrol', region_name=region)
    
    if operation == "create":
        response = cloudcontrol.create_resource(
            TypeName=resource_type,
            DesiredState=json.dumps(properties)
        )
        # Poll for completion
        # Returns SUCCESS or FAILED with details
```

**Polling for Completion:**
- Cloud Control API is asynchronous
- Agent polls `get_resource_request_status()` until SUCCESS/FAILED
- Waits up to ~60 seconds for completion

---

### Step 9: Generate Human-Friendly Summary (aws_agent.py)

AWS result is sent back to AI to create a user-friendly response:

**File:** `aws_agent.py - _generate_summary()`
```python
def _generate_summary(self, tool_name, tool_result, user_question):
    summary_prompt = SUMMARY_PROMPT.format(
        tool_name=tool_name,
        tool_result=json.dumps(tool_result),
        user_question=user_question
    )
    # AI generates: "✅ Successfully created S3 bucket 'my-photos' in eu-north-1"
```

---

### Step 10: Response to User (chat.py)

Final response displayed in Streamlit:

**File:** `chat.py:40-42`
```python
data = response.json()
reply = data.get("response", "⚠️ No reply received.")
st.markdown(reply)
```

---

## Visual Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  1. USER INPUT (Streamlit - chat.py)                                        │
│     "Create an S3 bucket named my-photos"                                   │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  2. HTTP POST to FastAPI (chat.py → main.py)                                │
│     POST http://localhost:8000/chat                                         │
│     Body: { "message": "...", "history": [...] }                            │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  3. FastAPI ENDPOINT (main.py)                                              │
│     Receives request, calls process_request()                               │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  4. PROCESSOR (processor.py)                                                │
│     Creates AWSAgenticAgent, calls agent.process_request()                  │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  5. AWS AGENT INIT (aws_agent.py)                                           │
│     - Reads AI_PROVIDER from .env (gemini/claude)                           │
│     - Initializes AI client                                                 │
│     - Tests AWS connection                                                  │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  6. SEND TO AI (aws_agent.py)                                               │
│     - Loads tools from tools.json                                           │
│     - Sends user message + tool definitions to AI                           │
│     - AI decides: text response OR function call                            │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                          ┌─────────┴─────────┐
                          ▼                   ▼
                    TEXT RESPONSE       FUNCTION CALL
                    (return text)       (aws_cloud_control)
                                              │
                                              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  7. AI RETURNS FUNCTION CALL                                                │
│     { "name": "aws_cloud_control", "args": {...} }                          │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  8. EXECUTE AWS OPERATION (aws_agent.py)                                    │
│     - Calls AWS Cloud Control API via boto3                                 │
│     - Polls for completion (SUCCESS/FAILED)                                 │
│     - Returns result with details                                           │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  9. GENERATE SUMMARY (aws_agent.py)                                         │
│     - Sends AWS result back to AI                                           │
│     - AI creates human-friendly summary                                     │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  10. RESPONSE TO USER (chat.py)                                             │
│      Displays: "✅ Successfully created S3 bucket 'my-photos'"              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Key Files & Their Roles

| File | Role | Key Functions |
|------|------|---------------|
| `chat.py` | Streamlit UI | Captures user input, displays responses |
| `main.py` | FastAPI server | HTTP endpoint `/chat` |
| `processor.py` | Bridge | Instantiates agent, calls `process_request` |
| `aws_agent.py` | Core logic | AI interaction, AWS operations |
| `tools.json` | Tool definitions | Tells AI what functions it can call |
| `prompt.py` | System prompts | Defines AI behavior and personality |
| `aws_config.py` | AWS config | Credentials & session management |

---

## Supported Operations (tools.json)

### 1. aws_cloud_control
- **create** - Create new AWS resources
- **read** - Get details of a specific resource
- **list** - List all resources of a type
- **update** - Modify existing resources
- **delete** - Remove resources

### 2. cloudwatch_logs
- Query Lambda function error logs
- Filter by time range

---

## Example User Queries

| User Says | AI Action | AWS Operation |
|-----------|-----------|---------------|
| "Show me all my S3 buckets" | `aws_cloud_control` | `list` on `AWS::S3::Bucket` |
| "Create bucket named photos" | `aws_cloud_control` | `create` on `AWS::S3::Bucket` |
| "Delete bucket old-data" | `aws_cloud_control` | `delete` on `AWS::S3::Bucket` |
| "Check Lambda errors" | `cloudwatch_logs` | Query CloudWatch Logs |
