from fastapi import APIRouter, UploadFile, File, HTTPException
from services.graph.builder import parse_csv, build_graph, make_id, generate_source_id
from db.neo4j_client import db
from datetime import datetime

router = APIRouter()

@router.post("/csv")
async def upload_csv(
    file: UploadFile = File(...),
    user_name: str = "Me",
    user_title: str = "",
    user_email: str = "",
    auth_email: str = "",
    is_additional: bool = False
):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files accepted")

    contents = await file.read()
    df = parse_csv(contents)

    source_id = generate_source_id() if is_additional else None

    stats = build_graph(df, {"name": user_name, "title": user_title, "email": user_email}, source_id=source_id)

    user_id = make_id(user_name, user_email)

    # Link auth email to the Person node so we can restore sessions later
    if auth_email:
        if not is_additional:
            db.run_write("""
                MATCH (p:Person {id: $user_id})
                SET p.auth_email = $auth_email
            """, user_id=user_id, auth_email=auth_email)
        else:
            # We must link the main authenticated user to this new bridge proxy
            db.run_write("""
                MATCH (u:Person {auth_email: $auth_email, is_user: true})
                MATCH (bridge:Person {id: $user_id})
                MERGE (u)-[:KNOWS {source_id: 'primary'}]->(bridge)
            """, auth_email=auth_email, user_id=user_id)

    # Store source metadata so we can list/delete later
    if source_id:
        db.run_write("""
            MERGE (s:ConnectionSource {id: $source_id})
            SET s.owner_name = $owner_name,
                s.owner_email = $owner_email,
                s.owner_person_id = $owner_person_id,
                s.uploaded_at = $uploaded_at,
                s.connection_count = $count,
                s.filename = $filename,
                s.auth_email = $auth_email
        """, source_id=source_id,
             owner_name=user_name,
             owner_email=user_email,
             owner_person_id=user_id,
             uploaded_at=datetime.utcnow().isoformat(),
             count=stats["persons"],
             filename=file.filename or "connections.csv",
             auth_email=auth_email)

    return {
        "success": True,
        "user_id": user_id,
        "source_id": source_id,
        "stats": stats,
        "message": f"Graph built: {stats['persons']} people, {stats['companies']} companies"
    }
