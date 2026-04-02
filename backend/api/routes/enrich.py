from fastapi import APIRouter, Depends, HTTPException
from services.enrichment.scrapfly_enricher import enrich_profile
from db.neo4j_client import db
from api.routes.auth import get_current_user

router = APIRouter()


@router.post("/profile")
async def enrich_connection(
    person_id: str,
    profile_url: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Enrich a single profile on-demand. Only call for top candidates.
    Requires authentication.
    """
    owner_user_id = current_user["id"]
    person_rows = db.run(
        """
        MATCH (root:Person)
        WHERE (root.is_user = true OR root.is_source = true)
          AND coalesce(root.owner_user_id, root.id) = $owner_id
        MATCH (root)-[:KNOWS*1..2]->(p:Person {id: $person_id, owner_user_id: $owner_id})
        RETURN p
        LIMIT 1
        """,
        owner_id=owner_user_id,
        person_id=person_id,
    )
    if not person_rows:
        raise HTTPException(status_code=404, detail="Person not found in your network")

    enriched = await enrich_profile(profile_url)

    if enriched:
        db.run_write("""
            MATCH (p:Person {id: $id})
            SET p.enriched = true,
                p.headline = $headline,
                p.location = $location
        """, id=person_id, **{k: v for k, v in enriched.items() if k in ["headline", "location"]})

    return {"person_id": person_id, "enriched_data": enriched}
