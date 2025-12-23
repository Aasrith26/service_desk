"""
Cached Clinic Knowledge Service
Provides fast, in-memory cached access to clinic data
Eliminates database lag for patient-facing calls
"""

from functools import lru_cache
from typing import Optional, Dict
import logging
import json
from datetime import datetime, timedelta

from core.services.clinic_info_service import ClinicInfoService

logger = logging.getLogger(__name__)


class CachedClinicService:
    """
    Cached wrapper around ClinicInfoService
    Cache is refreshed automatically after 5 minutes
    """
    
    _cache = {}
    _cache_timestamps = {}
    _cache_ttl = timedelta(minutes=5)  # 5-minute cache TTL
    
    @classmethod
    def get_clinic_by_phone_cached(cls, phone_number: str) -> Optional[Dict]:
        """
        Get clinic with full knowledge base, cached in memory
        
        Args:
            phone_number: Phone number from incoming call
            
        Returns:
            Complete clinic knowledge dict (cached)
        """
        # Check cache first
        if phone_number in cls._cache:
            cache_time = cls._cache_timestamps.get(phone_number)
            if cache_time and datetime.now() - cache_time < cls._cache_ttl:
                logger.info(f"✓ Cache HIT for {phone_number}")
                return cls._cache[phone_number]
            else:
                logger.info(f"Cache expired for {phone_number}, refreshing...")
        else:
            logger.info(f"Cache MISS for {phone_number}, fetching from DB...")
        
        # Fetch from database
        try:
            clinic = ClinicInfoService.get_clinic_by_phone(phone_number)
            if not clinic:
                logger.warning(f"No clinic found for {phone_number}")
                return None
            
            # Get complete knowledge base
            knowledge = ClinicInfoService.get_clinic_knowledge(clinic.id)
            
            # Cache it
            cls._cache[phone_number] = knowledge
            cls._cache_timestamps[phone_number] = datetime.now()
            
            logger.info(f"✓ Cached clinic '{clinic.name}' for {phone_number}")
            return knowledge
            
        except Exception as e:
            logger.error(f"Error fetching clinic data: {e}")
            return None
    
    @classmethod
    def invalidate_cache(cls, phone_number: Optional[str] = None):
        """
        Invalidate cache for a specific clinic or all clinics
        
        Args:
            phone_number: Specific phone to invalidate, or None for all
        """
        if phone_number:
            cls._cache.pop(phone_number, None)
            cls._cache_timestamps.pop(phone_number, None)
            logger.info(f"Invalidated cache for {phone_number}")
        else:
            cls._cache.clear()
            cls._cache_timestamps.clear()
            logger.info("Cleared all clinic caches")
    
    @classmethod
    def preload_clinic(cls, phone_number: str):
        """
        Preload clinic data into cache
        Call this on server startup for known clinics
        
        Args:
            phone_number: Phone number to preload
        """
        logger.info(f"Preloading clinic for {phone_number}...")
        cls.get_clinic_by_phone_cached(phone_number)
    
    @classmethod
    def get_cache_stats(cls) -> Dict:
        """Get cache statistics"""
        return {
            "cached_clinics": len(cls._cache),
            "cache_phones": list(cls._cache.keys()),
            "ttl_minutes": cls._cache_ttl.total_seconds() / 60
        }


# Convenience function for voice client
def get_cached_clinic_knowledge(phone_number: str) -> Optional[Dict]:
    """
    Get clinic knowledge with caching (ZERO LAG for patients)
    
    Args:
        phone_number: Incoming call phone number
        
    Returns:
        Complete clinic knowledge dict from cache or DB
    """
    return CachedClinicService.get_clinic_by_phone_cached(phone_number)


def preload_all_clinics():
    """
    Preload all clinic data on server startup
    Ensures first call has zero lag
    """
    logger.info("Preloading all clinics into cache...")
    
    # Known clinic phones - add your clinic phones here
    known_phones = [
        "+16203509655",  # Health Plus Clinic (Twilio number - Keep for reference)
        "03348052448",   # Health Plus Clinic (Exotel Landline)
        "09513886363",   # Health Plus Clinic (New Exotel Number)
        # Add more clinic phones here
    ]
    
    for phone in known_phones:
        try:
            CachedClinicService.preload_clinic(phone)
        except Exception as e:
            logger.error(f"Failed to preload {phone}: {e}")
    
    stats = CachedClinicService.get_cache_stats()
    logger.info(f"✓ Preloaded {stats['cached_clinics']} clinics into cache")
