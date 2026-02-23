import boto3
import os
from dotenv import load_dotenv

load_dotenv()

class AWSConfig:
    def __init__(self):
        self.access_key = os.getenv('AWS_ACCESS_KEY_ID')
        self.secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
        self.region = os.getenv('AWS_DEFAULT_REGION', 'eu-north-1')
        
    def get_session(self):
        """Get AWS session with basic credentials"""
        session = boto3.Session(
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            region_name=self.region
        )
        return session
    
    def validate_connection(self):
        """Test AWS connection"""
        try:
            session = self.get_session()
            sts = session.client('sts')
            identity = sts.get_caller_identity()
            print(f"✅ AWS Connection successful! Account: {identity['Account']}")
            return True
        except Exception as e:
            print(f"❌ AWS Connection failed: {e}")
            return False
        
if __name__ == "__main__":
    config = AWSConfig()
    config.validate_connection()