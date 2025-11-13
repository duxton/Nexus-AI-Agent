#!/usr/bin/env python3
"""
Setup script for Custom APIs - Products RAG and Outlets Text2SQL
Initializes databases, vector stores, and sample data
"""

import os
import sys
import asyncio

def setup_environment():
    """Setup environment and dependencies"""
    print("🔧 Setting up environment...")

    # Check if required packages are installed
    required_packages = [
        'fastapi', 'uvicorn', 'pydantic', 'openai',
        'faiss-cpu', 'sentence-transformers', 'sqlalchemy'
    ]

    missing_packages = []
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing_packages.append(package)

    if missing_packages:
        print(f"❌ Missing packages: {', '.join(missing_packages)}")
        print("📦 Install with: pip install " + " ".join(missing_packages))
        return False

    print("✅ All required packages are installed")
    return True

def setup_directories():
    """Create necessary directories"""
    print("📁 Creating directories...")

    directories = ['data', 'logs']
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"   ✓ {directory}/")

def setup_sample_data():
    """Setup sample product data"""
    print("📦 Setting up product data...")

    try:
        from scrape_zus_products import ZUSProductScraper

        scraper = ZUSProductScraper()
        products = scraper.scrape_drinkware_products()

        if products:
            scraper.save_products(products, "zus_drinkware_products.json")
            print(f"   ✓ Created product data: {len(products)} items")
        else:
            print("   ⚠️  No products scraped, using fallback data")

    except Exception as e:
        print(f"   ❌ Error setting up product data: {e}")
        return False

    return True

def setup_vector_store():
    """Initialize product vector store"""
    print("🔍 Setting up product vector store...")

    try:
        from product_kb import product_kb

        if product_kb.initialize(force_rebuild=True):
            print("   ✓ Vector store initialized successfully")
            product_kb._initialized = True
        else:
            print("   ❌ Vector store initialization failed")
            return False

    except Exception as e:
        print(f"   ❌ Error setting up vector store: {e}")
        return False

    return True

def setup_outlets_database():
    """Initialize outlets database"""
    print("🏪 Setting up outlets database...")

    try:
        from outlets_db import initialize_outlets_db

        initialize_outlets_db()
        print("   ✓ Outlets database initialized successfully")

    except Exception as e:
        print(f"   ❌ Error setting up outlets database: {e}")
        return False

    return True

def test_apis():
    """Test that APIs are working"""
    print("🧪 Testing API functionality...")

    try:
        # Test product KB
        from product_kb import product_kb
        result = product_kb.query("test query")
        if result and "answer" in result:
            print("   ✓ Product KB working")
        else:
            print("   ⚠️  Product KB test returned unexpected result")

        # Test outlets DB
        from outlets_db import text2sql
        result = text2sql.query("test query")
        if result and "success" in result:
            print("   ✓ Outlets Text2SQL working")
        else:
            print("   ⚠️  Outlets Text2SQL test returned unexpected result")

    except Exception as e:
        print(f"   ❌ Error testing APIs: {e}")
        return False

    return True

def check_environment_variables():
    """Check required environment variables"""
    print("🔑 Checking environment variables...")

    required_vars = ['OPENAI_API_KEY']
    missing_vars = []

    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)

    if missing_vars:
        print(f"   ⚠️  Missing environment variables: {', '.join(missing_vars)}")
        print("   💡 Create a .env file or set these variables")
        print("   Example .env content:")
        print("   OPENAI_API_KEY=your_openai_api_key_here")
        return False

    print("   ✓ Required environment variables are set")
    return True

def main():
    """Main setup function"""
    print("🚀 CUSTOM APIs SETUP SCRIPT")
    print("Setting up Products RAG and Outlets Text2SQL")
    print("=" * 50)

    success = True

    # Step 1: Environment check
    if not setup_environment():
        success = False

    # Step 2: Environment variables
    if not check_environment_variables():
        print("   ⚠️  Some features may not work without proper configuration")

    # Step 3: Create directories
    setup_directories()

    # Step 4: Setup sample data
    if not setup_sample_data():
        success = False

    # Step 5: Initialize vector store
    if not setup_vector_store():
        success = False

    # Step 6: Initialize outlets database
    if not setup_outlets_database():
        success = False

    # Step 7: Test functionality
    if not test_apis():
        print("   ⚠️  Some API tests failed, but setup may still be functional")

    # Final summary
    print("\n" + "=" * 50)
    if success:
        print("✅ SETUP COMPLETED SUCCESSFULLY!")
        print("\n🎯 Next Steps:")
        print("1. Start the server: uvicorn main:app --reload --port 8000")
        print("2. Test APIs: python demo_custom_apis.py")
        print("3. Run tests: python -m pytest test_custom_apis.py -v")
        print("4. View docs: http://localhost:8000/docs")
        print("\n📚 Check CUSTOM_APIS_DOCUMENTATION.md for detailed usage")
    else:
        print("❌ SETUP COMPLETED WITH ERRORS")
        print("Check the error messages above and resolve issues before running")

    print("=" * 50)

if __name__ == "__main__":
    main()