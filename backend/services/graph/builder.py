"""
Parses LinkedIn CSV and builds the Neo4j graph.

CSV columns (LinkedIn export):
  First Name, Last Name, Email Address, Company, Position, Connected On, LinkedIn URL
"""
import pandas as pd
import hashlib
import re
import logging
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from db.neo4j_client import db
from config import settings

logger = logging.getLogger(__name__)

# In-process cache for company domain lookups (survives across requests, cleared on restart)
_company_url_cache: dict[str, str] = {}

def company_to_logo_url(company_name: str) -> str:
    """Logo URLs are proxied server-side so API tokens never reach the browser."""
    return ""

def company_to_url(company_name: str) -> str:
    """Find the correct url of a company based on its name via Clearbit Autocomplete.
    Results are cached in-process to avoid repeat HTTP calls for the same company."""
    if not company_name:
        return ""

    # Check in-process cache first
    if company_name in _company_url_cache:
        return _company_url_cache[company_name]
    
    try:
        response = requests.get(
            "https://autocomplete.clearbit.com/v1/companies/suggest",
            params={"query": company_name},
            timeout=5,
        )
        response.raise_for_status()
        suggestions = response.json()
        if suggestions:
            domain = suggestions[0].get("domain", "")
            url = f"https://{domain}" if domain else ""
            _company_url_cache[company_name] = url
            return url
    except requests.RequestException as e:
        logger.warning("Error fetching company URL for '%s': %s", company_name, e)
    
    _company_url_cache[company_name] = ""
    return ""


def _resolve_company_urls_batch(company_names: list[str], max_workers: int = 10) -> dict[str, str]:
    """Resolve URLs for a list of *unique* company names in parallel threads.
    Uses the in-process cache and only makes HTTP calls for cache misses."""
    results: dict[str, str] = {}
    to_fetch: list[str] = []

    for name in company_names:
        if not name:
            continue
        if name in _company_url_cache:
            results[name] = _company_url_cache[name]
        else:
            to_fetch.append(name)

    if not to_fetch:
        return results

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_name = {executor.submit(company_to_url, name): name for name in to_fetch}
        for future in as_completed(future_to_name):
            name = future_to_name[future]
            try:
                results[name] = future.result()
            except Exception as e:
                logger.warning("Error resolving URL for '%s': %s", name, e)
                results[name] = ""

    return results


def parse_csv(file_bytes: bytes) -> pd.DataFrame:
    import io
    # LinkedIn CSVs have a 3-line header — skip it
    df = pd.read_csv(io.BytesIO(file_bytes), skiprows=3)
    df.columns = df.columns.str.strip()
    df = df.fillna("")
    
    # User-defined fields
    df["Initials"] = df["First Name"].str[0] + df["Last Name"].str[0]

    # Deduplicate company names and resolve URLs in parallel
    unique_companies = df["Company"].dropna().unique().tolist()
    url_map = _resolve_company_urls_batch(unique_companies)
    df["CompanyURL"] = df["Company"].map(url_map).fillna("")
    
    return df

def make_id(name: str, email: str = "") -> str:
    raw = f"{name}{email}".lower().strip()
    return hashlib.md5(raw.encode()).hexdigest()[:12]


def make_scoped_id(owner_user_id: str, name: str, email: str = "") -> str:
    raw = f"{owner_user_id}|{name}|{email}".lower().strip()
    return hashlib.md5(raw.encode()).hexdigest()[:12]


def _find_existing_person_id(owner_user_id: str, name: str, email: str, company: str) -> str | None:
    """
    Try to find an existing Person node that likely represents the same individual.

    Matching strategy (high-confidence only):
      1. Exact email match.
      2. Exact normalized name + company match.
    """
    # 1. Email match (highest confidence)
    if email:
        rows = db.run(
            """
            MATCH (p:Person)
            WHERE p.owner_user_id = $owner_user_id
              AND toLower(p.email) = toLower($email)
            RETURN p.id AS id
            LIMIT 1
            """,
            owner_user_id=owner_user_id,
            email=email,
        )
        if rows:
            return rows[0]["id"]

    # 2. Name + company match (still high confidence)
    if name and company:
        rows = db.run(
            """
            MATCH (p:Person)-[:WORKS_AT]->(c:Company)
            WHERE p.owner_user_id = $owner_user_id
              AND toLower(p.name) = toLower($name)
              AND toLower(c.name) = toLower($company)
            RETURN p.id AS id
            LIMIT 1
            """,
            owner_user_id=owner_user_id,
            name=name,
            company=company,
        )
        if rows:
            return rows[0]["id"]

    return None


def build_graph(df: pd.DataFrame, user: dict) -> dict:
    """
    Nodes:
      (:Person {id, name, title, email, profile_url, connected_on, is_recruiter, initials})
      (:Company {name})
    Relationships:
      (you)-[:KNOWS]->(connection)
      (connection)-[:WORKS_AT]->(company)
      (you)-[:WORKS_AT]->(your_companies)
    """
    stats = {"persons": 0, "companies": 0, "relationships": 0}

    # Create the root/source person node for this CSV
    user_name = user.get("name") or "Me"
    user_initials = "".join([part[0].upper() for part in user_name.split() if part])
    user_id = user.get("id") or make_id(user_name, user.get("email", ""))

    is_user = bool(user.get("is_user", True))
    is_source = bool(user.get("is_source", False) or is_user)
    network_name = user.get("network_name") or ("Primary Network" if is_user else "Imported Network")
    owner_user_id = user.get("owner_user_id") or user_id

    db.run_write(
        """
        MERGE (p:Person {id: $id})
        SET p.name = $name,
            p.title = $title,
            p.is_user = $is_user,
            p.is_source = $is_source,
            p.initials = $initials,
            p.owner_user_id = $owner_user_id,
            p.network_name = $network_name
    """,
        id=user_id,
        name=user_name,
        title=user.get("title", ""),
        is_user=is_user,
        is_source=is_source,
        initials=user_initials,
        owner_user_id=owner_user_id,
        network_name=network_name,
    )

    recruiter_keywords = ["recruiter", "talent acquisition", "hiring", "hr", "people ops", "talent partner"]
    
    batch = []

    for _, row in df.iterrows():
        name = f"{row.get('First Name', '')} {row.get('Last Name', '')}".strip()
        if not name:
            continue

        email = row.get("Email Address", "")
        company = row.get("Company", "").strip()
        company_url = row.get("CompanyURL", "").strip()
        title = row.get("Position", "").strip()
        connected_on = row.get("Connected On", "")
        profile_url = row.get("URL", "")

        # Decide whether to merge with an existing person node
        existing_id = _find_existing_person_id(owner_user_id, name, email, company)
        person_id = existing_id or make_scoped_id(owner_user_id, name, email)

        is_recruiter = any(kw in title.lower() for kw in recruiter_keywords)
        initials = row.get("Initials", "")
        logo_url = company_to_logo_url(company) if company else ""

        batch.append({
            "person_id": person_id,
            "name": name,
            "email": email,
            "company": company,
            "company_url": company_url,
            "title": title,
            "connected_on": connected_on,
            "profile_url": profile_url,
            "is_recruiter": is_recruiter,
            "initials": initials,
            "logo_url": logo_url,
            "owner_user_id": owner_user_id,
        })
        
    if not batch:
        return stats
        
    query = """
        MERGE (u:Person {id: $user_id})
        SET u.name = $user_name,
            u.title = $user_title,
            u.is_user = $user_is_user,
            u.is_source = $user_is_source,
            u.initials = $user_initials,
            u.owner_user_id = $owner_user_id,
            u.network_name = $network_name
        
        WITH u
        UNWIND $batch AS row
        
        MERGE (c:Person {id: row.person_id})
        SET c.name = row.name,
            c.title = row.title,
            c.email = row.email,
            c.profile_url = row.profile_url,
            c.connected_on = row.connected_on,
            c.is_recruiter = row.is_recruiter,
            c.degree = 1,
            c.initials = row.initials,
            c.owner_user_id = row.owner_user_id
            
        MERGE (u)-[:KNOWS]->(c)
        
        FOREACH (_ IN CASE WHEN row.company <> "" THEN [1] ELSE [] END |
            MERGE (comp:Company {name: row.company})
            SET comp.logo = row.logo_url,
                comp.url = row.company_url
            MERGE (c)-[:WORKS_AT]->(comp)
        )
    """

    db.run_write(query, 
        user_id=user_id,
        user_name=user["name"],
        user_title=user.get("title", ""),
        user_initials=user_initials,
        user_is_user=is_user,
        user_is_source=is_source,
        owner_user_id=owner_user_id,
        network_name=network_name,
        batch=batch
    )
    
    stats["persons"] = len(batch)
    stats["relationships"] = len(batch) * 2 # approximation
    stats["companies"] = len(set([b["company"] for b in batch if b["company"]]))

    return stats
