#!/usr/bin/env python3
"""
Simple import test for HALO framework.
This script tests basic imports without requiring all dependencies.
"""

import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.abspath('.'))

def test_basic_imports():
    """Test basic imports that don't require external dependencies."""
    try:
        # Test config module
        from halo.config import HALOConfig, get_config, load_config
        print("✅ Config module imports successfully")
        
        # Test models module
        from halo.models import VideoChunk, ProcessingResult, CacheEntry
        print("✅ Models module imports successfully")
        
        # Test basic config creation
        config = HALOConfig()
        print("✅ HALOConfig creation successful")
        
        print("\n🎉 Basic HALO imports working correctly!")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_package_structure():
    """Test that the package structure is correct."""
    try:
        import halo
        print(f"✅ HALO package version: {halo.__version__}")
        print(f"✅ HALO author: {halo.__author__}")
        print(f"✅ HALO email: {halo.__email__}")
        
        # Check that __all__ is defined
        if hasattr(halo, '__all__'):
            print(f"✅ HALO exports {len(halo.__all__)} items")
        else:
            print("❌ HALO __all__ not defined")
            
        return True
        
    except Exception as e:
        print(f"❌ Package structure error: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Testing HALO Framework Imports")
    print("=" * 40)
    
    success = True
    
    # Test basic imports
    if not test_basic_imports():
        success = False
    
    # Test package structure
    if not test_package_structure():
        success = False
    
    print("\n" + "=" * 40)
    if success:
        print("🎉 All tests passed! HALO is ready to use.")
        print("\n📝 Next steps:")
        print("1. Install dependencies: pip install -r requirements.txt")
        print("2. Set your API key: export GEMINI_API_KEY='your_key'")
        print("3. Run the demo: python demo.py")
    else:
        print("❌ Some tests failed. Please check the errors above.")
        sys.exit(1) 