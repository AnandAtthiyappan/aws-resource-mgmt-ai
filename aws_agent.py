import json
import os
from dotenv import load_dotenv
from aws_config import AWSConfig
from typing import Dict, Any, List, Optional
from prompt import SYSTEM_PROMPT, SUMMARY_PROMPT
from datetime import datetime, timedelta

load_dotenv(override=True)

class AWSAgenticAgent:
    def __init__(self):
        # Determine AI provider from environment variable
        self.ai_provider = os.getenv('AI_PROVIDER', 'claude').lower()
        
        if self.ai_provider == 'gemini':
            self._init_gemini()
        elif self.ai_provider == 'claude':
            self._init_claude()
        else:
            raise ValueError(
                f"❌ Invalid AI_PROVIDER: {self.ai_provider}\n"
                "Supported providers: 'claude' or 'gemini'"
            )
        
        self.aws_config = AWSConfig()
        #self._test_aws_connection()
    
    def _init_claude(self):
        """Initialize Anthropic Claude"""
        import anthropic
        
        anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')
        anthropic_model = os.getenv('ANTHROPIC_MODEL', 'claude-3-5-sonnet-latest').strip().strip('"').strip("'")

        if not anthropic_api_key:
            raise ValueError(
                "❌ ANTHROPIC_API_KEY not found in environment variables.\n"
                "Please add ANTHROPIC_API_KEY to your .env file.\n"
                "Get your key from: https://console.anthropic.com/"
            )
        
        self.client = anthropic.Anthropic(api_key=anthropic_api_key)
        self.model_name = anthropic_model
        print(f"✅ Using Anthropic Claude ({self.model_name})")
    
    def _init_gemini(self):
        """Initialize Google Gemini"""
        import google.generativeai as genai
        
        google_api_key = os.getenv('GOOGLE_API_KEY')
        google_model = (os.getenv('GOOGLE_MODEL', 'gemini-2.5-flash') or '').strip().strip('"').strip("'")
        if google_model and not google_model.startswith('gemini-'):
            google_model = f"gemini-{google_model}"

        if not google_api_key:
            raise ValueError(
                "❌ GOOGLE_API_KEY not found in environment variables.\n"
                "Please add GOOGLE_API_KEY to your .env file.\n"
                "Get your key from: https://makersuite.google.com/app/apikey"
            )
        
        genai.configure(api_key=google_api_key)
        self.genai = genai
        self.model_name = google_model
        print(f"✅ Using Google Gemini ({self.model_name})")
    
    def _test_aws_connection(self):
        """Test only AWS connection to reduce API load"""
        print("🔍 Testing AWS connection...")
        
        if not self.aws_config.validate_connection():
            raise Exception("AWS connection failed")
            
        print("✅ AWS connection successful!")
        print(f"ℹ️  {self.ai_provider.capitalize()} AI connection will be tested on first use")

    def _build_system_prompt(self) -> str:
        """Build system prompt for AWS operations"""
        return SYSTEM_PROMPT

    def _load_tools_config(self) -> List[Dict]:
        """Load tools configuration from unified tools.json"""
        json_path = os.path.join(os.path.dirname(__file__), "tools.json")
        with open(json_path, "r") as f:
            return json.load(f)

    def _format_tools(self):
        """Define tools for AI provider"""
        if self.ai_provider == 'claude':
            return self._format_tools_claude()
        elif self.ai_provider == 'gemini':
            return self._format_tools_gemini()
    
    def _format_tools_claude(self) -> List[Dict]:
        """Format tools for Claude (uses input_schema key)"""
        tools_config = self._load_tools_config()
        return [
            {
                "name": tool["name"],
                "description": tool["description"],
                "input_schema": tool["schema"]
            }
            for tool in tools_config
        ]
    
    def _format_tools_gemini(self) -> List:
        """Format tools for Gemini (uses parameters key)"""
        from google.generativeai.types import FunctionDeclaration, Tool
        
        tools_config = self._load_tools_config()
        function_declarations = [
            FunctionDeclaration(
                name=tool["name"],
                description=tool["description"],
                parameters=tool["schema"]
            )
            for tool in tools_config
        ]
        
        return [Tool(function_declarations=function_declarations)] 

    def _to_json_compatible(self, value: Any) -> Any:
        """Convert SDK/protobuf objects (e.g., MapComposite) to JSON-safe Python types."""
        if value is None or isinstance(value, (str, int, float, bool)):
            return value

        if isinstance(value, dict):
            return {str(k): self._to_json_compatible(v) for k, v in value.items()}

        if isinstance(value, (list, tuple, set)):
            return [self._to_json_compatible(item) for item in value]

        if hasattr(value, "items"):
            try:
                return {str(k): self._to_json_compatible(v) for k, v in value.items()}
            except Exception:
                pass

        if hasattr(value, "__iter__") and not isinstance(value, (bytes, bytearray)):
            try:
                return [self._to_json_compatible(item) for item in value]
            except Exception:
                pass

        if hasattr(value, "to_dict"):
            try:
                return self._to_json_compatible(value.to_dict())
            except Exception:
                pass

        return str(value)

    def _execute_aws_operation(self, operation: str, resource_type: str, 
                              identifier: str = None, properties: Dict = None, 
                              region: str = "eu-north-1") -> Dict[str, Any]:
        """Execute AWS Cloud Control API operation"""
        
        try:
            session = self.aws_config.get_session()
            cloudcontrol = session.client('cloudcontrol', region_name=region)
            normalized_properties = self._to_json_compatible(properties) if properties is not None else None
            
            print(f"🔧 Executing {operation} on {resource_type}")
            print(f"🔧 Properties: {normalized_properties}")
            print(f"🔧 Region: {region}")
            
            if operation == "create":
                try:
                    import time
                    response = cloudcontrol.create_resource(
                        TypeName=resource_type,
                        DesiredState=json.dumps(normalized_properties) if normalized_properties else "{}"
                    )
                    print(f"🔧 AWS Response: {response}")
                    
                    # Check if we actually got a valid response
                    if 'ProgressEvent' not in response:
                        return {
                            "status": "error",
                            "operation": operation,
                            "resource_type": resource_type,
                            "error": "Invalid response from AWS Cloud Control API",
                            "aws_response": str(response)
                        }
                    
                    request_token = response.get('ProgressEvent', {}).get('RequestToken')
                    if not request_token:
                        return {
                            "status": "error",
                            "operation": operation,
                            "resource_type": resource_type,
                            "error": "No request token received from AWS",
                            "aws_response": str(response)
                        }
                    
                    # Poll for completion - Cloud Control API is asynchronous
                    print(f"🔧 Waiting for resource creation to complete (token: {request_token})...")
                    max_attempts = 4  # Wait up to ~60 seconds
                    for attempt in range(max_attempts):
                        status_response = cloudcontrol.get_resource_request_status(
                            RequestToken=request_token
                        )
                        progress_event = status_response.get('ProgressEvent', {})
                        op_status = progress_event.get('OperationStatus', '')
                        
                        print(f"🔧 Attempt {attempt + 1}/{max_attempts}: Status = {op_status}")
                        
                        if op_status == 'SUCCESS':
                            resource_id = progress_event.get('Identifier', '')
                            return {
                                "status": "success",
                                "operation": operation,
                                "resource_type": resource_type,
                                "identifier": resource_id,
                                "message": f"Successfully created {resource_type}: {resource_id}",
                                "aws_response": str(status_response)
                            }
                        elif op_status == 'FAILED':
                            error_code = progress_event.get('ErrorCode', 'Unknown')
                            status_message = progress_event.get('StatusMessage', 'No details provided')
                            return {
                                "status": "error",
                                "operation": operation,
                                "resource_type": resource_type,
                                "error": f"Creation failed: {error_code} - {status_message}",
                                "aws_response": str(status_response)
                            }
                        elif op_status in ('CANCEL_COMPLETE', 'CANCEL_IN_PROGRESS'):
                            return {
                                "status": "error",
                                "operation": operation,
                                "resource_type": resource_type,
                                "error": "Operation was cancelled",
                                "aws_response": str(status_response)
                            }
                        
                        # Still IN_PROGRESS or PENDING, wait and retry
                        time.sleep(15)  # Wait before next status check
                    
                    # Timed out waiting
                    return {
                        "status": "timeout",
                        "operation": operation,
                        "resource_type": resource_type,
                        "request_token": request_token,
                        "message": f"Resource creation is taking longer than expected. Check AWS Console or use request token: {request_token}",
                        "aws_response": str(response)
                    }
                    
                except Exception as create_error:
                    print(f"🔧 Create Resource Error: {create_error}")
                    return {
                        "status": "error",
                        "operation": operation,
                        "resource_type": resource_type,
                        "error": f"Failed to create resource: {str(create_error)}",
                        "aws_error": str(create_error)
                    }
                
            elif operation == "list":
                try:
                    response = cloudcontrol.list_resources(TypeName=resource_type)
                    print(f"🔧 List Response: {response}")
                    
                    resources = response.get('ResourceDescriptions', [])
                    return {
                        "status": "success",
                        "operation": operation,
                        "resource_type": resource_type,
                        "count": len(resources),
                        "resources": [json.loads(r.get('Properties', '{}')) for r in resources[:5]],  # Limit to 5
                        "aws_response": str(response)
                    }
                    
                except Exception as list_error:
                    print(f"🔧 List Resources Error: {list_error}")
                    return {
                        "status": "error",
                        "operation": operation,
                        "resource_type": resource_type,
                        "error": f"Failed to list resources: {str(list_error)}",
                        "aws_error": str(list_error)
                    }
                
            elif operation == "read" and identifier:
                try:
                    response = cloudcontrol.get_resource(
                        TypeName=resource_type,
                        Identifier=identifier
                    )
                    print(f"🔧 Read Response: {response}")
                    
                    return {
                        "status": "success",
                        "operation": operation,
                        "resource_type": resource_type,
                        "identifier": identifier,
                        "properties": json.loads(response['ResourceDescription']['Properties']),
                        "aws_response": str(response)
                    }
                    
                except Exception as read_error:
                    print(f"🔧 Read Resource Error: {read_error}")
                    return {
                        "status": "error",
                        "operation": operation,
                        "resource_type": resource_type,
                        "identifier": identifier,
                        "error": f"Failed to read resource: {str(read_error)}",
                        "aws_error": str(read_error)
                    }
                
            else:
                return {
                    "status": "error",
                    "message": f"Operation {operation} not fully implemented in demo"
                }
                
        except Exception as e:
            print(f"🔧 General AWS Operation Error: {e}")
            return {
                "status": "error",
                "operation": operation,
                "resource_type": resource_type,
                "error": f"General AWS operation failed: {str(e)}",
                "aws_error": str(e)
            }

    def _query_cloudwatch_logs(self, function_name: str, hours_back: int = 1) -> Dict[str, Any]:
        """Query CloudWatch Logs for Lambda function errors"""
        
        try:
            session = self.aws_config.get_session()
            logs_client = session.client('logs')
            
            # Calculate time range
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=hours_back)
            
            # Find log group for the Lambda function
            log_group_name = f"/aws/lambda/{function_name}"
            
            # Filter for ERROR level logs
            response = logs_client.filter_log_events(
                logGroupName=log_group_name,
                startTime=int(start_time.timestamp() * 1000),
                endTime=int(end_time.timestamp() * 1000),
                filterPattern="ERROR"
            )
            
            error_logs = []
            for event in response.get('events', []):
                error_logs.append({
                    "timestamp": datetime.fromtimestamp(event['timestamp'] / 1000).isoformat(),
                    "message": event['message'],
                    "logStreamName": event['logStreamName']
                })
            
            return {
                "status": "success",
                "function_name": function_name,
                "hours_back": hours_back,
                "error_count": len(error_logs),
                "error_logs": error_logs[:10]  # Limit to 10 most recent errors
            }
            
        except Exception as e:
            return {
                "status": "error",
                "function_name": function_name,
                "error": str(e)
            }

    def _list_ecs_clusters(self, operation: str = "list", cluster_names: List[str] = None, 
                          region: str = "eu-north-1") -> Dict[str, Any]:
        """List or describe ECS clusters"""
        
        try:
            session = self.aws_config.get_session()
            ecs_client = session.client('ecs', region_name=region)
            
            if operation == "list":
                # List all cluster ARNs
                response = ecs_client.list_clusters()
                cluster_arns = response.get('clusterArns', [])
                
                if not cluster_arns:
                    return {
                        "status": "success",
                        "operation": "list",
                        "region": region,
                        "count": 0,
                        "clusters": [],
                        "message": "No ECS clusters found in this region"
                    }
                
                # Get details for all clusters
                describe_response = ecs_client.describe_clusters(clusters=cluster_arns)
                clusters = []
                for cluster in describe_response.get('clusters', []):
                    clusters.append({
                        "name": cluster.get('clusterName'),
                        "arn": cluster.get('clusterArn'),
                        "status": cluster.get('status'),
                        "running_tasks": cluster.get('runningTasksCount', 0),
                        "pending_tasks": cluster.get('pendingTasksCount', 0),
                        "active_services": cluster.get('activeServicesCount', 0),
                        "registered_instances": cluster.get('registeredContainerInstancesCount', 0)
                    })
                
                return {
                    "status": "success",
                    "operation": "list",
                    "region": region,
                    "count": len(clusters),
                    "clusters": clusters
                }
                
            elif operation == "describe" and cluster_names:
                # Describe specific clusters
                describe_response = ecs_client.describe_clusters(clusters=cluster_names)
                clusters = []
                for cluster in describe_response.get('clusters', []):
                    clusters.append({
                        "name": cluster.get('clusterName'),
                        "arn": cluster.get('clusterArn'),
                        "status": cluster.get('status'),
                        "running_tasks": cluster.get('runningTasksCount', 0),
                        "pending_tasks": cluster.get('pendingTasksCount', 0),
                        "active_services": cluster.get('activeServicesCount', 0),
                        "registered_instances": cluster.get('registeredContainerInstancesCount', 0),
                        "capacity_providers": cluster.get('capacityProviders', []),
                        "settings": cluster.get('settings', [])
                    })
                
                failures = describe_response.get('failures', [])
                
                return {
                    "status": "success",
                    "operation": "describe",
                    "region": region,
                    "count": len(clusters),
                    "clusters": clusters,
                    "failures": [{"arn": f.get('arn'), "reason": f.get('reason')} for f in failures] if failures else []
                }
            else:
                return {
                    "status": "error",
                    "error": "Invalid operation or missing cluster_names for describe operation"
                }
                
        except Exception as e:
            return {
                "status": "error",
                "operation": operation,
                "region": region,
                "error": str(e)
            }

    def _generate_summary(self, tool_name: str, tool_result: Dict[str, Any], user_question: str) -> str:
        """Generate natural language summary from tool results"""
        
        try:
            summary_prompt = SUMMARY_PROMPT.format(
                tool_name=tool_name,
                tool_result=json.dumps(tool_result, indent=2),
                user_question=user_question
            )
            
            if self.ai_provider == 'claude':
                response = self.client.messages.create(
                    model=self.model_name,
                    max_tokens=500,
                    messages=[{"role": "user", "content": summary_prompt}]
                )
                return response.content[0].text
            
            elif self.ai_provider == 'gemini':
                summary_model = self.genai.GenerativeModel(self.model_name)
                response = summary_model.generate_content(summary_prompt)
                return response.text
            
        except Exception as e:
            return f"Summary generation failed: {str(e)}"

    def process_request(self, user_input: str, history: List[Dict]) -> str:
        """Process request using configured AI provider"""
        if self.ai_provider == 'claude':
            return self._process_request_claude(user_input, history)
        elif self.ai_provider == 'gemini':
            return self._process_request_gemini(user_input, history)
    
    def _process_request_claude(self, user_input: str, history: List[Dict]) -> str:
        """Process request using Claude"""
        history.append({"role": "user", "content": user_input})

        try:
            response = self.client.messages.create(
                model=self.model_name,
                max_tokens=2000,
                system=self._build_system_prompt(),
                messages=history,
                tools=self._format_tools()
            )

            response_content = ""

            for content_block in response.content:
                if content_block.type == "text":
                    print("Received a TEXT Response from Claude: ****************")
                    print("RAW Response:", content_block.text)
                    response_content += content_block.text

                elif content_block.type == "tool_use":
                    print("Received a Tool Use Request from Claude: ****************")
                    print("Tool Name:", content_block.name)
                    print("Tool Input:", content_block.input)
                    tool_name = content_block.name
                    tool_input = content_block.input

                    if tool_name == "aws_cloud_control":
                        result = self._execute_aws_operation(**tool_input)
                        summary = self._generate_summary(tool_name, result, user_input)
                        response_content += f"\n\n🤖 AI Summary:\n{summary}"
                    
                    elif tool_name == "cloudwatch_logs":
                        result = self._query_cloudwatch_logs(**tool_input)
                        summary = self._generate_summary(tool_name, result, user_input)
                        response_content += f"\n\n🤖 AI Summary:\n{summary}"
                    
                    elif tool_name == "ecs_clusters":
                        result = self._list_ecs_clusters(**tool_input)
                        summary = self._generate_summary(tool_name, result, user_input)
                        response_content += f"\n\n🤖 AI Summary:\n{summary}"

            history.append({"role": "assistant", "content": response_content})
            return response_content

        except Exception as e:
            error_msg = f"❌ Error processing request: {str(e)}"
            print(error_msg)
            return error_msg
    
    def _process_request_gemini(self, user_input: str, history: List[Dict]) -> str:
        """Process request using Gemini"""
        try:
            # Build conversation history for Gemini
            chat_history = []
            for msg in history:
                role = "user" if msg["role"] == "user" else "model"
                chat_history.append({"role": role, "parts": [msg["content"]]})
            
            # Create model with tools and system instruction
            model = self.genai.GenerativeModel(
                model_name=self.model_name,
                tools=self._format_tools(),
                system_instruction=self._build_system_prompt()  # ✅ Proper system prompt
            )
            
            # Start chat with history
            chat = model.start_chat(history=chat_history)
            
            response = chat.send_message(user_input)
            response_content = ""
            
            # Handle function calls and text
            if response.candidates[0].content.parts:
                for part in response.candidates[0].content.parts:
                    if hasattr(part, 'function_call') and part.function_call:
                        fc = part.function_call
                        print("Received a Function Call from Gemini: ****************")
                        print("Function Name:", fc.name)
                        print("Function Args:", dict(fc.args))
                        
                        tool_name = fc.name
                        tool_input = self._to_json_compatible(dict(fc.args))
                        
                        if tool_name == "aws_cloud_control":
                            result = self._execute_aws_operation(**tool_input)
                            summary = self._generate_summary(tool_name, result, user_input)
                            response_content += f"\n\n🤖 AI Summary:\n{summary}"
                        
                        elif tool_name == "cloudwatch_logs":
                            result = self._query_cloudwatch_logs(**tool_input)
                            summary = self._generate_summary(tool_name, result, user_input)
                            response_content += f"\n\n🤖 AI Summary:\n{summary}"
                        
                        elif tool_name == "ecs_clusters":
                            result = self._list_ecs_clusters(**tool_input)
                            summary = self._generate_summary(tool_name, result, user_input)
                            response_content += f"\n\n🤖 AI Summary:\n{summary}"
                    
                    elif hasattr(part, 'text') and part.text:
                        print("Received a TEXT Response from Gemini: ****************")
                        print("RAW Response:", part.text)
                        response_content += part.text
            
            history.append({"role": "user", "content": user_input})
            history.append({"role": "assistant", "content": response_content})
            
            return response_content if response_content else "No response generated"
            
        except Exception as e:
            error_msg = f"❌ Error processing request: {str(e)}"
            print(error_msg)
            import traceback
            traceback.print_exc()
            return error_msg
