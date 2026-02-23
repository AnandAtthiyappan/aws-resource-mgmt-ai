"""
Test script to diagnose AI API connection issues
Supports both Anthropic Claude and Google Gemini
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv(override=True)

def test_claude_connection():
    """Test Anthropic Claude API connection"""
    print("=" * 60)
    print("🔍 Testing Anthropic Claude API Connection")
    print("=" * 60)
    
    try:
        import anthropic
    except ImportError:
        print("❌ anthropic package not installed")
        print("   Run: pip install anthropic")
        return False
    
    api_key = os.getenv('ANTHROPIC_API_KEY')
    api_model = os.getenv('ANTHROPIC_MODEL', 'claude-3-5-sonnet-latest').strip().strip('"').strip("'")

    if not api_key:
        print("❌ ANTHROPIC_API_KEY not found in environment variables")
        print("   Get your key from: https://console.anthropic.com/")
        return False
    
    print(f"✅ API Key found: {api_key[:15]}...{api_key[-4:]}")
    print(f"   Key length: {len(api_key)} characters")
    
    try:
        client = anthropic.Anthropic(api_key=api_key)
        print("✅ Claude client initialized")
    except Exception as e:
        print(f"❌ Failed to initialize client: {e}")
        return False
    
    print("\n🔄 Testing API call...")
    try:
        response = client.messages.create(
            model=api_model,
            max_tokens=100,
            messages=[
                {"role": "user", "content": "Say 'Connection successful!' if you can read this."}
            ]
        )
        
        print("✅ API call successful!")
        print(f"📝 Response: {response.content[0].text}")
        print(f"📊 Model: {response.model}")
        return True
        
    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {e}")
        if "Connection error" in str(e):
            print("\n💡 Possible causes:")
            print("   - No internet connection")
            print("   - Firewall blocking api.anthropic.com")
            print("   - Proxy configuration needed")
        return False


def test_gemini_connection():
    """Test Google Gemini API connection"""
    print("=" * 60)
    print("🔍 Testing Google Gemini API Connection")
    print("=" * 60)
    
    try:
        import google.generativeai as genai
    except ImportError:
        print("❌ google-generativeai package not installed")
        print("   Run: pip install google-generativeai")
        return False
    
    api_key = os.getenv('GOOGLE_API_KEY')
    api_model = (os.getenv('GOOGLE_MODEL', 'gemini-2.5-flash') or '').strip().strip('"').strip("'")
    if api_model and not api_model.startswith('gemini-'):
        api_model = f"gemini-{api_model}"
    if not api_key:
        print("❌ GOOGLE_API_KEY not found in environment variables")
        print("   Get your key from: https://makersuite.google.com/app/apikey")
        return False
    
    print(f"✅ API Key found: {api_key[:10]}...{api_key[-4:]}")
    print(f"   Key length: {len(api_key)} characters")
    
    try:
        genai.configure(api_key=api_key)
        print("✅ Gemini API configured")
    except Exception as e:
        print(f"❌ Failed to configure Gemini: {e}")
        return False
    
    print("\n🔄 Testing API call...")
    try:
        model = genai.GenerativeModel(api_model)
        response = model.generate_content("Say 'Connection successful!' if you can read this.")
        
        print("✅ API call successful!")
        print(f"📝 Response: {response.text}")
        print(f"📊 Model: {api_model}")
        return True
        
    except Exception as e:
        error_type = type(e).__name__
        print(f"❌ Error: {error_type}: {e}")
        
        if "API_KEY_INVALID" in str(e) or "invalid" in str(e).lower():
            print("\n💡 Your API key is invalid or expired")
            print("   Get a new key from: https://makersuite.google.com/app/apikey")
        elif "quota" in str(e).lower() or "rate" in str(e).lower():
            print("\n💡 You've hit the rate limit. Wait a moment and try again.")
        else:
            print("\n💡 Possible causes:")
            print("   - No internet connection")
            print("   - Firewall blocking generativelanguage.googleapis.com")
            print("   - Invalid API key format")
        
        return False


def main():
    """Test the configured AI provider"""
    print("\n" + "🤖 AI API Connection Test" + "\n")
    
    ai_provider = os.getenv('AI_PROVIDER', 'claude').lower()
    print(f"📍 Configured AI Provider: {ai_provider}")
    print("")
    
    if ai_provider == 'claude':
        success = test_claude_connection()
    elif ai_provider == 'gemini':
        success = test_gemini_connection()
    else:
        print(f"❌ Invalid AI_PROVIDER: {ai_provider}")
        print("   Supported providers: 'claude' or 'gemini'")
        success = False
    
    print("\n" + "=" * 60)
    if success:
        print("✅ All tests passed! Your connection is working.")
        print(f"   You can now use the application with {ai_provider.capitalize()}")
    else:
        print("❌ Connection test failed. Review the errors above.")
        
        # Show instructions for switching provider
        print("\n💡 Want to try the other provider?")
        if ai_provider == 'claude':
            print("   1. Get a Google API key from: https://makersuite.google.com/app/apikey")
            print("   2. Add GOOGLE_API_KEY to your .env file")
            print("   3. Change AI_PROVIDER=gemini in .env")
        else:
            print("   1. Get an Anthropic API key from: https://console.anthropic.com/")
            print("   2. Add ANTHROPIC_API_KEY to your .env file")
            print("   3. Change AI_PROVIDER=claude in .env")
    
    print("=" * 60)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
