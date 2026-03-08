import httpx
from typing import Optional, List, Dict, Any
from config import settings

class BackboardService:
    """
    Service for interacting with Backboard.io API.
    Provides unified access to LLMs with persistent memory/threads.
    """
    
    BASE_URL = "https://api.backboard.io/v1"
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.backboard_api_key
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    async def generate_completion(
        self, 
        prompt: str, 
        model: str = "gpt-4o-mini",
        assistant_id: Optional[str] = None,
        thread_id: Optional[str] = None
    ) -> str:
        """
        Generates a completion using Backboard's unified API.
        """
        if not self.api_key:
            raise ValueError("Backboard API key not found")

        # Simplified direct chat/completion endpoint based on common unified API patterns
        # If assistant/thread IDs are provided, they would be used for context.
        # For simple outreach generation, we can use the messages/completions style.
        
        payload = {
            "model": model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "stream": False
        }
        
        # Note: Implementation might need adjustment based on specific Backboard API structure
        # (e.g., /threads/{id}/messages or /chat/completions)
        # Using a standard /chat/completions style as a likely unified interface.
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.BASE_URL}/chat/completions",
                    json=payload,
                    headers=self.headers,
                    timeout=30.0
                )
                response.raise_for_status()
                data = response.json()
                
                if "choices" in data and len(data["choices"]) > 0:
                    return data["choices"][0]["message"]["content"].strip()
                elif "content" in data:
                    return data["content"].strip()
                else:
                    return str(data)
            except Exception as e:
                print(f"Backboard error: {e}")
                raise

# Global instance
backboard = BackboardService()
