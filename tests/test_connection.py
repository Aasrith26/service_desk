"""
Test connection to Azure GPT-Realtime API
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.realtime_client import RealtimeClient
from utils.logger import get_logger

logger = get_logger(__name__)


async def test_connection():
    """Test basic connection to Azure GPT-Realtime API."""
    logger.info("=" * 60)
    logger.info("Testing Azure GPT-Realtime Connection")
    logger.info("=" * 60)
    
    client = RealtimeClient()
    
    try:
        # Test connection
        if not await client.connect():
            logger.error("[FAIL] Connection failed")
            return False
        
        logger.info("[PASS] Successfully connected to Azure GPT-Realtime API")
        
        # Test sending a text message
        logger.info("\nSending test message...")
        await client.send_message("Hello! Is Dr. Kavya available tomorrow?")
        
        # Wait for response
        await asyncio.sleep(3)
        
        logger.info("[PASS] Test message sent and processed")
        
        return True
    
    except Exception as e:
        logger.error(f"[FAIL] Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        await client.disconnect()


async def test_context_retrieval():
    """Test context retrieval from clinic data."""
    logger.info("\n" + "=" * 60)
    logger.info("Testing Context Retrieval")
    logger.info("=" * 60)
    
    from core.context_retriever import ContextRetriever
    
    retriever = ContextRetriever()
    
    try:
        # Test various queries
        test_queries = [
            "Is Dr. Kavya available?",
            "I need to see a cardiologist",
            "Tell me about pediatrics",
            "What are your visiting hours?",
            "Can I reschedule my appointment?"
        ]
        
        for query in test_queries:
            logger.info(f"\nQuery: {query}")
            context = retriever.get_context(query)
            logger.info("Context retrieved:")
            for line in context.split('\n')[:5]:
                logger.info(f"  {line}")
                lines = context.split('\n')
                if len(lines) > 5:
                    logger.info(f"  ... ({len(lines) - 5} more lines)")
        
        logger.info("\n[PASS] Context retrieval working correctly")
        return True
    
    except Exception as e:
        logger.error(f"[FAIL] Context test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests."""
    results = []
    
    # Test connection
    result1 = await test_connection()
    results.append(("Connection Test", result1))
    
    # Test context
    result2 = await test_context_retrieval()
    results.append(("Context Retrieval Test", result2))
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("TEST SUMMARY")
    logger.info("=" * 60)
    
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        logger.info(f"{test_name}: {status}")
    
    all_passed = all(result for _, result in results)
    logger.info("\n" + ("All tests passed!" if all_passed else "Some tests failed"))
    
    return all_passed


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
