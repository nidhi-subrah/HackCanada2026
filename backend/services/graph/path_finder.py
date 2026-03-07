"""
Core path-finding engine.
Finds shortest paths from the user to a target company through the graph.
"""
from db.neo4j_client import db

def find_paths_to_company(user_id: str, target_company: str) -> list[dict]:
    """
    Uses Neo4j shortest path to find all 1st and 2nd degree connections
    at the target company, ordered by relevance.
    """
    # Direct connections (1st degree)
    first_degree = db.run("""
        MATCH (u:Person {id: $user_id})-[:KNOWS]->(p:Person)-[:WORKS_AT]->(c:Company)
        WHERE toLower(c.name) CONTAINS toLower($company)
        RETURN p, c, 1 as degree
    """, user_id=user_id, company=target_company)

    # 2nd degree connections
    second_degree = db.run("""
        MATCH (u:Person {id: $user_id})-[:KNOWS]->(bridge:Person)-[:KNOWS]->(p:Person)-[:WORKS_AT]->(c:Company)
        WHERE toLower(c.name) CONTAINS toLower($company)
        AND NOT (u)-[:KNOWS]->(p)
        RETURN p, c, bridge, 2 as degree
    """, user_id=user_id, company=target_company)

    # 3rd degree connections
    third_degree = db.run("""
        MATCH (u:Person {id: $user_id})-[:KNOWS]->(bridge1:Person)-[:KNOWS]->(bridge2:Person)-[:KNOWS]->(p:Person)-[:WORKS_AT]->(c:Company)
        WHERE toLower(c.name) CONTAINS toLower($company)
        AND NOT (u)-[:KNOWS*1..2]-(p)
        RETURN p, c, bridge1, bridge2, 3 as degree
    """, user_id=user_id, company=target_company)

    return {"first_degree": first_degree, "second_degree": second_degree, "third_degree": third_degree}

def get_graph_for_company(user_id: str, target_company: str) -> dict:
    """Returns nodes + edges for the graph visualizer."""
    result = db.run("""
        MATCH path = (u:Person {id: $user_id})-[:KNOWS*1..2]-(p:Person)-[:WORKS_AT]->(c:Company)
        WHERE toLower(c.name) CONTAINS toLower($company)
        RETURN nodes(path) as nodes, relationships(path) as rels
        LIMIT 100
    """, user_id=user_id, company=target_company)
    return result
