from fastapi import APIRouter, Query
from services.graph.path_finder import find_paths_to_company
from services.scoring.relevance import rank_connections
from models.person import UserProfile

router = APIRouter()

@router.get("/company")
def search_company(
    company: str = Query(...),
    user_id: str = Query(...),
    user_name: str = Query("Me"),
    user_companies: str = Query(""),    # comma-separated
    user_schools: str = Query(""),      # comma-separated
):
    user_profile = UserProfile(
        name=user_name,
        companies=[c.strip() for c in user_companies.split(",") if c.strip()],
        schools=[s.strip() for s in user_schools.split(",") if s.strip()],
    )

    paths = find_paths_to_company(user_id, company)

    # Flatten all candidates
    candidates = []
    for r in paths["first_degree"]:
        p = dict(r["p"])
        p["degree"] = 1
        candidates.append(p)

    for r in paths["second_degree"]:
        p = dict(r["p"])
        p["degree"] = 2
        p["bridge"] = dict(r["bridge"])
        candidates.append(p)

    for r in paths["third_degree"]:
        p = dict(r["p"])
        p["degree"] = 3
        p["bridge"] = dict(r["bridge1"])
        p["bridge2"] = dict(r["bridge2"])
        candidates.append(p)

    ranked = rank_connections(user_profile, candidates, company)

    return {
        "company": company,
        "total_connections": len(ranked),
        "first_degree_count": len(paths["first_degree"]),
        "second_degree_count": len(paths["second_degree"]),
        "third_degree_count": len(paths["third_degree"]),
        "recruiters": [c for c in ranked if c.get("is_recruiter")],
        "top_connections": ranked[:10],
    }
