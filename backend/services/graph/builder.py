"""
Parses LinkedIn CSV and builds the Neo4j graph.

CSV columns (LinkedIn export):
  First Name, Last Name, Email Address, Company, Position, Connected On, LinkedIn URL
"""
import pandas as pd
import hashlib
import uuid
from db.neo4j_client import db

def parse_csv(file_bytes: bytes) -> pd.DataFrame:
    import io
    # LinkedIn CSVs have a 3-line header — skip it
    df = pd.read_csv(io.BytesIO(file_bytes), skiprows=3)
    df.columns = df.columns.str.strip()
    df = df.fillna("")
    return df

def make_id(name: str, email: str = "") -> str:
    raw = f"{name}{email}".lower().strip()
    return hashlib.md5(raw.encode()).hexdigest()[:12]

def generate_source_id() -> str:
    return uuid.uuid4().hex[:12]

def build_graph(df: pd.DataFrame, user: dict, source_id: str | None = None) -> dict:
    """
    Nodes:
      (:Person {id, name, title, email, profile_url, connected_on, is_recruiter})
      (:Company {name})
    Relationships:
      (you)-[:KNOWS]->(connection)
      (connection)-[:WORKS_AT]->(company)
      (you)-[:WORKS_AT]->(your_companies)
    """
    stats = {"persons": 0, "companies": 0, "relationships": 0}

    user_id = make_id(user["name"], user.get("email", ""))

    # Create the user node
    db.run_write("""
        MERGE (p:Person {id: $id})
        SET p.name = $name, p.title = $title, p.is_user = true
    """, id=user_id, name=user["name"], title=user.get("title", ""))

    # If a source_id is provided, mark this person as a source owner
    if source_id:
        db.run_write("""
            MERGE (p:Person {id: $id})
            SET p.is_source_owner = true
        """, id=user_id)

    recruiter_keywords = ["recruiter", "talent acquisition", "hiring", "hr", "people ops", "talent partner"]

    for _, row in df.iterrows():
        name = f"{row.get('First Name', '')} {row.get('Last Name', '')}".strip()
        if not name:
            continue

        email = row.get("Email Address", "")
        company = row.get("Company", "").strip()
        title = row.get("Position", "").strip()
        connected_on = row.get("Connected On", "")
        profile_url = row.get("URL", "")
        person_id = make_id(name, email)

        is_recruiter = any(kw in title.lower() for kw in recruiter_keywords)

        # Upsert Person
        db.run_write("""
            MERGE (p:Person {id: $id})
            SET p.name = $name,
                p.title = $title,
                p.email = $email,
                p.profile_url = $profile_url,
                p.connected_on = $connected_on,
                p.is_recruiter = $is_recruiter,
                p.degree = 1
        """, id=person_id, name=name, title=title, email=email,
             profile_url=profile_url, connected_on=connected_on,
             is_recruiter=is_recruiter)
        stats["persons"] += 1

        # Relationship: you → connection (tagged with source_id if provided)
        if source_id:
            db.run_write("""
                MATCH (u:Person {id: $user_id}), (c:Person {id: $conn_id})
                MERGE (u)-[r:KNOWS]->(c)
                SET r.source_id = $source_id
            """, user_id=user_id, conn_id=person_id, source_id=source_id)
        else:
            db.run_write("""
                MATCH (u:Person {id: $user_id}), (c:Person {id: $conn_id})
                MERGE (u)-[:KNOWS]->(c)
            """, user_id=user_id, conn_id=person_id)
        stats["relationships"] += 1

        if company:
            # Upsert Company
            db.run_write("""
                MERGE (co:Company {name: $name})
            """, name=company)
            stats["companies"] += 1

            # Relationship: connection → company
            db.run_write("""
                MATCH (p:Person {id: $person_id}), (co:Company {name: $company})
                MERGE (p)-[:WORKS_AT]->(co)
            """, person_id=person_id, company=company)
            stats["relationships"] += 1

    return stats
