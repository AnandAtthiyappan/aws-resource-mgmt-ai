from aws_agent import AWSAgenticAgent
from typing import List, Dict

def process_request(user_message: str, history: List[Dict]) -> str:
    # Example logic
    agent = AWSAgenticAgent()
    return agent.process_request(user_message, history=history)
