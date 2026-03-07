from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from datetime import datetime, timezone
from services.ai.message_generator import generate_outreach_message
from db.neo4j_client import db
from api.routes.auth import get_current_user

router = APIRouter()


class MessageRequest(BaseModel):
    target_person: dict
    target_company: str
    bridge_person: dict | None = None


class MessageLogRequest(BaseModel):
    target_name: str
    target_company: str
    channel: str = "copy"  # "copy" or "email"


@router.post("/generate")
async def generate_message(
    req: MessageRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Generate an outreach message. User info is extracted from JWT.
    """
    try:
        user = {
            "id": current_user["id"],
            "name": current_user["name"] or current_user["email"].split("@")[0],
            "email": current_user["email"],
        }
        
        message = generate_outreach_message(
            user=user,
            target_person=req.target_person,
            target_company=req.target_company,
            context={"bridge_person": req.bridge_person}
        )
        return {"message": message}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/log")
async def log_message(
    req: MessageLogRequest,
    current_user: dict = Depends(get_current_user)
):
    """Log an outreach event (copy or email send) for tracking."""
    user_id = current_user["id"]
    try:
        db.run_write(
            """
            MATCH (u:Person {id: $user_id})
            CREATE (m:SentMessage {
                target_name: $target_name,
                target_company: $target_company,
                channel: $channel,
                created_at: $created_at
            })
            CREATE (u)-[:SENT]->(m)
            """,
            user_id=user_id,
            target_name=req.target_name,
            target_company=req.target_company,
            channel=req.channel,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
def get_message_stats(current_user: dict = Depends(get_current_user)):
    """Return outreach stats for the authenticated user."""
    user_id = current_user["id"]
    result = db.run(
        """
        MATCH (u:Person {id: $user_id})-[:SENT]->(m:SentMessage)
        RETURN count(m) as messages_sent
        """,
        user_id=user_id,
    )
    return {"messages_sent": result[0]["messages_sent"] if result else 0}
