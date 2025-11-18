"""
Simple script to check if the API server is ready.
Run this periodically to see when the system is fully initialized.
"""
import requests
import time
from datetime import datetime

def check_health():
    """Check if API server is responding and healthy."""
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            return True, data
        else:
            return False, {"error": f"Status code: {response.status_code}"}
    except requests.exceptions.ConnectionError:
        return False, {"error": "API server not responding yet"}
    except requests.exceptions.Timeout:
        return False, {"error": "Request timed out"}
    except Exception as e:
        return False, {"error": str(e)}

def main():
    """Main monitoring loop."""
    print("🔍 Checking API Server Status...")
    print("=" * 60)
    
    is_ready, result = check_health()
    
    if is_ready:
        print("✅ API SERVER IS READY!")
        print("\nService Status:")
        for service, status in result.get("services", {}).items():
            emoji = "✅" if status == "ok" else "❌"
            print(f"  {emoji} {service}: {status}")
        
        print("\n🎉 System is fully operational!")
        print("\n📋 Next Steps:")
        print("  1. Open http://localhost:3000 in your browser")
        print("  2. Fill out your profile")
        print("  3. Generate your meal plan")
        print("\n💡 Tip: First generation takes 30-60 seconds")
    else:
        print("⏳ API server is still initializing...")
        print(f"\nStatus: {result.get('error', 'Unknown')}")
        print("\n📥 Likely still downloading or loading the model")
        print("   This can take 30-45 minutes on first run")
        print("\n💡 You can:")
        print("  - Open http://localhost:3000 and start filling the form")
        print("  - Run this script again in a few minutes")
        print("  - Check the API server terminal for progress")

if __name__ == "__main__":
    main()
