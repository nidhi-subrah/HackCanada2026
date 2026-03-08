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
        Generates a completion using Backboard's Assistant/Thread flow.
        """
        if not self.api_key:
            raise ValueError("Backboard API key not found")

        # 1. Create a thread
        async with httpx.AsyncClient() as client:
            thread_resp = await client.post(
                f"{self.BASE_URL}/threads",
                headers=self.headers,
                json={}
            )
            thread_resp.raise_for_status()
            thread_data = thread_resp.json()
            curr_thread_id = thread_data["id"]

            # 2. Add message to thread
            msg_resp = await client.post(
                f"{self.BASE_URL}/threads/{curr_thread_id}/messages",
                headers=self.headers,
                data={
                    "role": "user",
                    "content": prompt
                }
            )
            msg_resp.raise_for_status()

            # 3. Create a run
            run_payload = {"assistant_id": assistant_id or "default"}
            if model:
                run_payload["model"] = model
                
            run_resp = await client.post(
                f"{self.BASE_URL}/threads/{curr_thread_id}/runs",
                headers=self.headers,
                json=run_payload
            )
            run_resp.raise_for_status()
            run_data = run_resp.json()
            run_id = run_data["id"]

            # 4. Poll for completion
            for _ in range(30): # 30 seconds timeout
                status_resp = await client.get(
                    f"{self.BASE_URL}/threads/{curr_thread_id}/runs/{run_id}",
                    headers=self.headers
                )
                status_data = status_resp.json()
                if status_data["status"] == "completed":
                    # 5. Get messages
                    msgs_resp = await client.get(
                        f"{self.BASE_URL}/threads/{curr_thread_id}/messages",
                        headers=self.headers
                    )
                    msgs_data = msgs_resp.json()
                    # Return the latest assistant message
                    for msg in msgs_data.get("data", []):
                        if msg["role"] == "assistant":
                            return msg["content"][0]["text"]["value"]
                    return "No response from assistant"
                elif status_data["status"] in ["failed", "cancelled", "expired"]:
                    raise Exception(f"Backboard run failed: {status_data['status']}")
                
                import asyncio
                await asyncio.sleep(1)
            
            raise Exception("Backboard request timed out")

# Global instance
backboard = BackboardService()
