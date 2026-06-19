import logging
import os
from typing import Optional
from fastapi import Header
from supabase import create_client, Client

logger = logging.getLogger(__name__)

_supabase_admin: Optional[Client] = None


def _get_supabase_admin() -> Optional[Client]:
    global _supabase_admin
    if _supabase_admin is None:
        url = os.environ.get("SUPABASE_URL", "")
        key = os.environ.get("SUPABASE_SERVICE_KEY", "")
        if url and key and "placeholder" not in url and "placeholder" not in key:
            try:
                _supabase_admin = create_client(url, key)
                logger.info("Supabase admin client initialized")
            except Exception as e:
                logger.warning(f"Failed to create Supabase admin client: {e}")
    return _supabase_admin


async def get_optional_user(authorization: Optional[str] = Header(None)):
    if not authorization:
        return None

    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        return None

    supabase = _get_supabase_admin()
    if not supabase:
        return None

    try:
        user_response = supabase.auth.get_user(jwt=token)
        if user_response and user_response.user:
            return user_response.user
    except Exception as e:
        logger.warning(f"Supabase JWT verification failed: {e}")

    return None
