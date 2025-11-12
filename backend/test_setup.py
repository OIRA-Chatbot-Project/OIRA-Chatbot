"""
Quick test script to verify the backend setup
Run this after installing dependencies to check if everything is configured correctly
"""

import sys
import os

def test_imports():
    """Test if all required packages can be imported"""
    print("Testing imports...")
    try:
        import fastapi
        print("✓ FastAPI")
        import sqlalchemy
        print("✓ SQLAlchemy")
        import chromadb
        print("✓ ChromaDB")
        from langchain_openai import ChatOpenAI, OpenAIEmbeddings
        print("✓ LangChain OpenAI")
        from langchain_chroma import Chroma
        print("✓ LangChain Chroma")
        import uvicorn
        print("✓ Uvicorn")
        from dotenv import load_dotenv
        print("✓ Python dotenv")
        print("\n✅ All imports successful!\n")
        return True
    except ImportError as e:
        print(f"\n❌ Import error: {e}\n")
        return False


def test_env():
    """Test if environment variables are set"""
    print("Testing environment variables...")
    from dotenv import load_dotenv
    load_dotenv()
    
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key and api_key.startswith("sk-"):
        print("✓ OPENAI_API_KEY is set")
        return True
    else:
        print("❌ OPENAI_API_KEY is not set or invalid")
        print("   Please set it in your .env file")
        return False


def test_database():
    """Test if database can be initialized"""
    print("\nTesting database initialization...")
    try:
        from database import init_db, engine
        init_db()
        print("✓ Database initialized successfully")
        
        # Check if tables were created
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        expected_tables = ['sessions', 'messages', 'feedback']
        missing_tables = [t for t in expected_tables if t not in tables]
        
        if missing_tables:
            print(f"⚠ Missing tables: {missing_tables}")
            return False
        else:
            print(f"✓ All tables created: {tables}")
            return True
            
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False


def test_chroma():
    """Test if ChromaDB can be accessed"""
    print("\nTesting ChromaDB connection...")
    try:
        import config
        if not os.path.exists(config.CHROMA_PATH):
            print(f"⚠ ChromaDB directory not found at {config.CHROMA_PATH}")
            print("   Run 'python ingest_database.py' to create the vector database")
            return False
        
        from chatbot_service import chatbot_service
        print(f"✓ ChromaDB connected at {config.CHROMA_PATH}")
        return True
        
    except Exception as e:
        print(f"❌ ChromaDB error: {e}")
        return False


def main():
    """Run all tests"""
    print("=" * 50)
    print("OIRA Chatbot Backend - Setup Verification")
    print("=" * 50 + "\n")
    
    results = []
    
    # Run tests
    results.append(("Imports", test_imports()))
    results.append(("Environment", test_env()))
    results.append(("Database", test_database()))
    results.append(("ChromaDB", test_chroma()))
    
    # Summary
    print("\n" + "=" * 50)
    print("SUMMARY")
    print("=" * 50)
    
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test_name:20} {status}")
    
    all_passed = all(result[1] for result in results)
    
    if all_passed:
        print("\n🎉 All tests passed! You can start the server with:")
        print("   python main.py")
        print("\n   Or:")
        print("   uvicorn main:app --reload")
    else:
        print("\n⚠ Some tests failed. Please fix the issues above.")
        
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
