"""
Simple script to start the FastAPI server.
"""
import sys
import uvicorn

if __name__ == "__main__":
    print("🚀 Starting Meal Planner API Server...")
    print("📍 Server will be available at: http://localhost:8000")
    print("📖 API docs at: http://localhost:8000/docs")
    print("⏹️  Press CTRL+C to stop\n")
    
    try:
        uvicorn.run(
            "src.main:app",
            host="127.0.0.1",
            port=8000,
            reload=True,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n\n✅ Server stopped")
    except Exception as e:
        print(f"\n❌ Error starting server: {e}")
        sys.exit(1)
