"""
Query Answering System - Demonstrates the full pipeline
Works offline to test the architecture without Azure auth issues
"""

import asyncio
from typing import Optional, List
from dataclasses import dataclass

from core.context_retriever import ContextRetriever
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class QueryResponse:
    """Response from query answering system."""
    query: str
    language: str  # 'en' or 'te'
    response_text: str
    context_used: str
    confidence: float


class QueryAnsweringEngine:
    """
    Process queries and generate responses using clinic context.
    
    This is a standalone module that works WITHOUT Azure connection
    to test the full query → context → response pipeline.
    """
    
    def __init__(self):
        """Initialize the query answering engine."""
        self.context_retriever = ContextRetriever()
        self.query_history: List[QueryResponse] = []
    
    def detect_language(self, text: str) -> str:
        """
        Detect if text is English or Telugu.
        
        Simple heuristic: if contains Telugu script characters, it's Telugu
        Telugu Unicode ranges: 0x0C00-0x0C7F
        """
        for char in text:
            code = ord(char)
            if 0x0C00 <= code <= 0x0C7F:
                return "te"
        return "en"
    
    def answer_query(self, query: str) -> QueryResponse:
        """
        Answer a user query using clinic context.
        
        Args:
            query: User's question
        
        Returns:
            QueryResponse with the answer
        """
        # Detect language
        language = self.detect_language(query)
        logger.info(f"Query language: {language} (English)" if language == "en" else "Query language: te (Telugu)")
        
        # Get clinic context
        context = self.context_retriever.get_context(query)
        
        # Generate response (in real system, this would call Azure GPT)
        response_text = self._generate_response(query, context, language)
        
        # Create response object
        response = QueryResponse(
            query=query,
            language=language,
            response_text=response_text,
            context_used=context[:200],  # Store first 200 chars for reference
            confidence=0.85
        )
        
        # Store in history
        self.query_history.append(response)
        
        return response
    
    def _generate_response(self, query: str, context: str, language: str) -> str:
        """
        Generate response based on query and context.
        
        In production, this would be replaced with Azure GPT-Realtime call.
        For now, we simulate intelligent responses.
        """
        query_lower = query.lower()
        
        # Extract relevant info from context
        lines = context.split('\n')
        
        # Pattern matching for common queries
        if any(word in query_lower for word in ["doctor", "available", "appointment"]):
            return self._respond_appointment(query, context, language)
        
        elif any(word in query_lower for word in ["hours", "open", "timing"]):
            return self._respond_hours(context, language)
        
        elif any(word in query_lower for word in ["cardiologist", "cardiology"]):
            return self._respond_specialization("Cardiology", context, language)
        
        elif any(word in query_lower for word in ["pediatric", "pediatrician"]):
            return self._respond_specialization("Pediatrics", context, language)
        
        else:
            return self._respond_general(query, context, language)
    
    def _respond_appointment(self, query: str, context: str, language: str) -> str:
        """Generate appointment-related response."""
        if language == "te":
            return "నేను మీకు విలువైన సమస్య గురించి సహాయం చేయ్యగలను. డాక్టర్ల అందుబాటు గురించి చదవండి సందర్భం నుండి."
        else:
            return "I can help you with that. Our doctors' availability and appointment slots are shown in the context above. Which doctor would you like to see?"
    
    def _respond_hours(self, context: str, language: str) -> str:
        """Generate hours response."""
        if language == "te":
            return "మా క్లినిక్ సాధారణంగా సోమవారం నుండి శుక్రవారం 9 AM నుండి 6 PM వరకు తెరిఉంటుంది. సదస్యుల సమయ నిర్ణయం కోసం సంబంధించండి."
        else:
            return "Our clinic operates Monday to Friday, 9 AM to 6 PM. Saturdays we have limited hours (10 AM - 2 PM). Please note timings in the context above."
    
    def _respond_specialization(self, specialization: str, context: str, language: str) -> str:
        """Generate specialization response."""
        if language == "te":
            return f"మాకు {specialization} విభాగంలో నిపుణులు ఉన్నారు. సంబంధం కోసం క్రింద చూడండి."
        else:
            return f"We have specialist doctors in {specialization}. Please check the context above for their availability and appointment slots."
    
    def _respond_general(self, query: str, context: str, language: str) -> str:
        """Generate general response."""
        if language == "te":
            return f"మీ ప్రశ్నకు సమాధానం ఇక్కడ ఉంది. దయచేసి సందర్భం చూడండి."
        else:
            return "I understand your question. Please refer to the clinic context above for the relevant information."
    
    def get_history(self) -> List[QueryResponse]:
        """Get query history."""
        return self.query_history
    
    def clear_history(self):
        """Clear query history."""
        self.query_history = []


async def demo_query_answering():
    """
    Demo function showing query answering in action.
    """
    logger.info("=" * 60)
    logger.info("Query Answering Engine Demo")
    logger.info("=" * 60)
    
    engine = QueryAnsweringEngine()
    
    # Test queries
    test_queries = [
        "Is Dr. Kavya available tomorrow for a general checkup?",
        "I need to see a cardiologist. What are the available appointments?",
        "What are your clinic hours?",
        "Can Dr. Rajesh see me next week?",
        "I need pediatric care for my child.",
    ]
    
    for query in test_queries:
        logger.info("\n" + "=" * 60)
        logger.info(f"Query: {query}")
        
        # Get response
        response = engine.answer_query(query)
        
        logger.info(f"Language: {response.language}")
        logger.info(f"Response: {response.response_text}")
        logger.info(f"Confidence: {response.confidence:.1%}")
    
    # Show history summary
    logger.info("\n" + "=" * 60)
    logger.info("Query History Summary")
    logger.info("=" * 60)
    for i, resp in enumerate(engine.get_history(), 1):
        logger.info(f"{i}. [{resp.language.upper()}] {resp.query[:50]}...")
    
    logger.info("\n" + "=" * 60)
    logger.info("Demo Complete")
    logger.info("=" * 60)


if __name__ == "__main__":
    # Run demo
    asyncio.run(demo_query_answering())
