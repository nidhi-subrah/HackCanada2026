from fastapi import APIRouter, Query
from db.neo4j_client import db
from services.graph.builder import make_id

router = APIRouter()

@router.get("/connections")
def get_connections(user_id: str = Query(...)):
    """Returns all 1st-degree connections for the user."""
    results = db.run("""
        MATCH (u:Person {id: $user_id})-[:KNOWS]->(p:Person)
        OPTIONAL MATCH (p)-[:WORKS_AT]->(c:Company)
        RETURN p, c
        ORDER BY p.name
        LIMIT 500
    """, user_id=user_id)

    connections = []
    for r in results:
        person = dict(r["p"])
        company = dict(r["c"]) if r.get("c") else {}
        person["company"] = company.get("name", "")
        person["degree"] = "1st"
        connections.append(person)

    return {"connections": connections, "total": len(connections)}

@router.get("/stats")
def get_stats(user_id: str = Query(...)):
    """Returns summary stats for the dashboard."""
    person_count = db.run("""
        MATCH (u:Person {id: $user_id})-[:KNOWS]->(p:Person)
        RETURN count(p) as count
    """, user_id=user_id)

    company_count = db.run("""
        MATCH (u:Person {id: $user_id})-[:KNOWS]->(p:Person)-[:WORKS_AT]->(c:Company)
        RETURN count(DISTINCT c) as count
    """, user_id=user_id)

    recruiter_count = db.run("""
        MATCH (u:Person {id: $user_id})-[:KNOWS]->(p:Person)
        WHERE p.is_recruiter = true
        RETURN count(p) as count
    """, user_id=user_id)

    top_companies = db.run("""
        MATCH (u:Person {id: $user_id})-[:KNOWS]->(p:Person)-[:WORKS_AT]->(c:Company)
        RETURN c.name as company, count(p) as connections
        ORDER BY connections DESC
        LIMIT 5
    """, user_id=user_id)

    return {
        "connections": person_count[0]["count"] if person_count else 0,
        "companies": company_count[0]["count"] if company_count else 0,
        "recruiters": recruiter_count[0]["count"] if recruiter_count else 0,
        "top_companies": top_companies,
    }

@router.get("/session")
def get_session(auth_email: str = Query(...)):
    """Look up existing graph user by their auth email.
    Returns user_id + user_name if they have previously uploaded data."""
    results = db.run("""
        MATCH (p:Person {auth_email: $email, is_user: true})
        RETURN p.id as user_id, p.name as user_name
        LIMIT 1
    """, email=auth_email)

    if results and results[0].get("user_id"):
        return {
            "found": True,
            "user_id": results[0]["user_id"],
            "user_name": results[0]["user_name"] or "",
        }
    return {"found": False}


@router.get("/overview")
def get_graph_overview(user_id: str = Query(...)):
    """Returns the full graph for the network visualizer with nodes + links.
    Includes source grouping so each CSV upload forms a visual cluster."""

    # Get the central user node
    user_rows = db.run("""
        MATCH (u:Person {id: $user_id})
        RETURN u
    """, user_id=user_id)

    if not user_rows:
        return {"nodes": [], "links": [], "groups": []}

    user_node = dict(user_rows[0]["u"])
    user_name = user_node.get("name", "You")

    # Get all KNOWS relationships with their source_id, up to 2 hops
    rows = db.run("""
        MATCH (a:Person)-[r:KNOWS]->(b:Person)
        WHERE a.id = $user_id OR (a)<-[:KNOWS]-(:Person {id: $user_id})
        WITH a, r, b LIMIT 1000
        OPTIONAL MATCH (a)-[:WORKS_AT]->(ca:Company)
        OPTIONAL MATCH (b)-[:WORKS_AT]->(cb:Company)
        RETURN a, r, ca, b, cb
    """, user_id=user_id)

    nodes = []
    links = []
    seen_nodes = set()
    seen_companies = set()
    node_groups = {}  # node_id -> source_id (first one wins for grouping)

    # Central user node — group "primary"
    nodes.append({
        "id": user_id,
        "name": user_name,
        "type": "user",
        "title": user_node.get("title", ""),
        "group": "primary",
    })
    seen_nodes.add(user_id)
    node_groups[user_id] = "primary"

    # Process all returned rows
    for r in rows:
        a = dict(r["a"])
        b = dict(r["b"])
        rel = dict(r["r"]) if r.get("r") else {}
        ca = dict(r["ca"]) if r.get("ca") else None
        cb = dict(r["cb"]) if r.get("cb") else None

        a_id = a.get("id")
        b_id = b.get("id")
        rel_source_id = rel.get("source_id", "primary")

        # Track group membership
        for pid in [a_id, b_id]:
            if pid and pid not in node_groups:
                node_groups[pid] = rel_source_id

        # Add nodes if not seen
        for person_node, comp_node in [(a, ca), (b, cb)]:
            pid = person_node.get("id")
            if pid and pid not in seen_nodes:
                node_type = "person"
                if person_node.get("is_source_owner"):
                    node_type = "source_owner"

                nodes.append({
                    "id": pid,
                    "name": person_node.get("name", ""),
                    "type": node_type,
                    "title": person_node.get("title", ""),
                    "is_recruiter": person_node.get("is_recruiter", False),
                    "group": node_groups.get(pid, "primary"),
                })
                seen_nodes.add(pid)

            if comp_node:
                cname = comp_node.get("name", "")
                if cname:
                    cid = f"company_{cname}"
                    if cid not in seen_companies:
                        nodes.append({
                            "id": cid,
                            "name": cname,
                            "type": "company",
                            "group": node_groups.get(pid, "primary") if pid else "primary",
                        })
                        seen_companies.add(cid)

                    # WORKS_AT link
                    if pid:
                        links.append({
                            "source": pid,
                            "target": cid,
                            "label": "WORKS_AT",
                        })

        if a_id and b_id:
            links.append({
                "source": a_id,
                "target": b_id,
                "label": "KNOWS",
                "source_id": rel_source_id,
            })

    # De-duplicate links
    unique_links = []
    seen_links = set()
    for link in links:
        key = f"{link['source']}-{link['target']}-{link['label']}"
        if key not in seen_links:
            seen_links.add(key)
            unique_links.append(link)

    # Build groups metadata from ConnectionSource nodes
    source_rows = db.run("""
        MATCH (s:ConnectionSource)
        RETURN s
        ORDER BY s.uploaded_at
    """)
    groups = [{"id": "primary", "name": "Your Connections", "color": "#8B5CF6"}]
    group_colors = ["#22d3ee", "#34d399", "#fbbf24", "#fb7185", "#a78bfa", "#f472b6", "#38bdf8"]
    for i, sr in enumerate(source_rows):
        s = dict(sr["s"])
        groups.append({
            "id": s.get("id", ""),
            "name": s.get("owner_name", "Unknown"),
            "color": group_colors[i % len(group_colors)],
        })

    return {"nodes": nodes, "links": unique_links, "groups": groups}

@router.get("/company/{company_name}")
def get_company_subgraph(company_name: str, user_id: str = Query(...)):
    """Returns the subgraph relevant to a specific company search."""
    result = db.run("""
        MATCH (u:Person {id: $user_id})-[:KNOWS]->(p:Person)-[:WORKS_AT]->(c:Company)
        WHERE toLower(c.name) CONTAINS toLower($company)
        RETURN u, p, c
        UNION
        MATCH (u:Person {id: $user_id})-[:KNOWS]->(bridge:Person)-[:KNOWS]->(p:Person)-[:WORKS_AT]->(c:Company)
        WHERE toLower(c.name) CONTAINS toLower($company)
        RETURN u, bridge as p, c
    """, user_id=user_id, company=company_name)
    return result

@router.get("/sources")
def list_sources():
    """Returns all uploaded connection sources."""
    results = db.run("""
        MATCH (s:ConnectionSource)
        RETURN s
        ORDER BY s.uploaded_at DESC
    """)
    sources = []
    for r in results:
        s = dict(r["s"])
        sources.append({
            "id": s.get("id", ""),
            "owner_name": s.get("owner_name", ""),
            "owner_email": s.get("owner_email", ""),
            "owner_person_id": s.get("owner_person_id", ""),
            "uploaded_at": s.get("uploaded_at", ""),
            "connection_count": s.get("connection_count", 0),
            "filename": s.get("filename", ""),
        })
    return {"sources": sources}

@router.delete("/sources/{source_id}")
def delete_source(source_id: str):
    """Deletes a connection source and its associated KNOWS relationships."""
    # Delete all KNOWS relationships tagged with this source_id
    db.run_write("""
        MATCH ()-[r:KNOWS {source_id: $source_id}]->()
        DELETE r
    """, source_id=source_id)

    # Delete the ConnectionSource node
    db.run_write("""
        MATCH (s:ConnectionSource {id: $source_id})
        DELETE s
    """, source_id=source_id)

    # Clean up orphaned Person nodes (no remaining relationships)
    db.run_write("""
        MATCH (p:Person)
        WHERE p.is_user IS NULL AND p.is_source_owner IS NULL
          AND NOT (p)-[:KNOWS]-() AND NOT (p)<-[:KNOWS]-()
        DETACH DELETE p
    """)

    return {"success": True, "message": f"Source {source_id} and associated connections removed"}
