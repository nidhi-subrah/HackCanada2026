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
            timeout=2,  # keep tight — this is on the upload hot path
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
    import time
    t0 = time.monotonic()
    # LinkedIn CSVs have a 3-line header — skip it
    df = pd.read_csv(io.BytesIO(file_bytes), skiprows=3)
    df.columns = df.columns.str.strip()
    df = df.fillna("")

    # User-defined fields
    df["Initials"] = df["First Name"].str[0] + df["Last Name"].str[0]
    logger.info("parse_csv: parsed %d rows in %.2fs", len(df), time.monotonic() - t0)

    # Deduplicate company names and resolve URLs in parallel
    unique_companies = df["Company"].dropna().unique().tolist()
    t0 = time.monotonic()
    url_map = _resolve_company_urls_batch(unique_companies)
    df["CompanyURL"] = df["Company"].map(url_map).fillna("")
    logger.info(
        "parse_csv: resolved %d company URLs in %.2fs",
        len(unique_companies),
        time.monotonic() - t0,
    )

    return df

def make_id(name: str, email: str = "") -> str:
    raw = f"{name}{email}".lower().strip()
    return hashlib.md5(raw.encode()).hexdigest()[:12]


def make_scoped_id(owner_user_id: str, name: str, email: str = "") -> str:
    raw = f"{owner_user_id}|{name}|{email}".lower().strip()
    return hashlib.md5(raw.encode()).hexdigest()[:12]


def _load_existing_person_index(owner_user_id: str) -> dict:
    """
    Preload every Person already stored for this owner so that per-row dedup
    lookups during a bulk upload become O(1) dict lookups instead of 2 Neo4j
    round-trips per row. A LinkedIn CSV with 2,000 connections previously
    issued up to 4,000 queries; now it issues a single query.
    """
    rows = db.run(
        """
        MATCH (p:Person)
        WHERE p.owner_user_id = $owner_user_id
        OPTIONAL MATCH (p)-[:WORKS_AT]->(c:Company)
        RETURN p.id AS id,
               toLower(coalesce(p.email, '')) AS email,
               toLower(coalesce(p.name, '')) AS name,
               toLower(coalesce(c.name, '')) AS company
        """,
        owner_user_id=owner_user_id,
    )

    by_email: dict[str, str] = {}
    by_name_company: dict[tuple[str, str], str] = {}
    for row in rows:
        pid = row["id"]
        if row["email"]:
            by_email.setdefault(row["email"], pid)
        if row["name"] and row["company"]:
            by_name_company.setdefault((row["name"], row["company"]), pid)

    return {"by_email": by_email, "by_name_company": by_name_company}


def _lookup_existing_id(
    index: dict, name: str, email: str, company: str
) -> str | None:
    """In-memory lookup against the preloaded index."""
    if email:
        match = index["by_email"].get(email.lower())
        if match:
            return match
    if name and company:
        match = index["by_name_company"].get((name.lower(), company.lower()))
        if match:
            return match
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
    import time
    stats = {"persons": 0, "companies": 0, "relationships": 0}

    # Create the root/source person node for this CSV
    user_name = user.get("name") or "Me"
    user_initials = "".join([part[0].upper() for part in user_name.split() if part])
    user_id = user.get("id") or make_id(user_name, user.get("email", ""))

    is_user = bool(user.get("is_user", True))
    is_source = bool(user.get("is_source", False) or is_user)
    network_name = user.get("network_name") or ("Primary Network" if is_user else "Imported Network")
    owner_user_id = user.get("owner_user_id") or user_id

    t0 = time.monotonic()
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
    logger.info("build_graph: owner upsert in %.2fs", time.monotonic() - t0)

    # Load the owner's existing persons in a single query so per-row dedup
    # lookups are in-memory instead of 2 round-trips per row.
    t0 = time.monotonic()
    person_index = _load_existing_person_index(owner_user_id)
    logger.info(
        "build_graph: preloaded %d existing persons in %.2fs",
        len(person_index["by_email"]) + len(person_index["by_name_company"]),
        time.monotonic() - t0,
    )

    recruiter_keywords = ["recruiter", "talent acquisition", "hiring", "hr", "people ops", "talent partner"]

    batch = []
    t0 = time.monotonic()
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

        # In-memory dedup against preloaded index
        existing_id = _lookup_existing_id(person_index, name, email, company)
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
    logger.info("build_graph: built %d-row batch in %.2fs", len(batch), time.monotonic() - t0)

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

    # Chunk the write so a single huge batch doesn't blow up transaction
    # memory on AuraDB or hit the Bolt frame size limit.
    CHUNK_SIZE = 500
    t0 = time.monotonic()
    for i in range(0, len(batch), CHUNK_SIZE):
        chunk = batch[i : i + CHUNK_SIZE]
        db.run_write(
            query,
            user_id=user_id,
            user_name=user["name"],
            user_title=user.get("title", ""),
            user_initials=user_initials,
            user_is_user=is_user,
            user_is_source=is_source,
            owner_user_id=owner_user_id,
            network_name=network_name,
            batch=chunk,
        )
        logger.info(
            "build_graph: wrote chunk %d-%d of %d",
            i + 1,
            i + len(chunk),
            len(batch),
        )
    logger.info("build_graph: neo4j writes done in %.2fs", time.monotonic() - t0)

    stats["persons"] = len(batch)
    stats["relationships"] = len(batch) * 2  # approximation
    stats["companies"] = len(set([b["company"] for b in batch if b["company"]]))

    return stats
