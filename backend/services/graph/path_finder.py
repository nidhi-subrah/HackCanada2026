"""
Core path-finding engine.
Finds shortest paths from the user to a target company through the graph.
"""
from db.neo4j_client import db


def find_paths_to_company(user_id: str, target_company: str) -> dict:
    """
    Find all 1st, 2nd, and 3rd degree connections at the target company.

    Degree semantics:
      1st: (you)-[:KNOWS]->(p)-[:WORKS_AT]->(Company)
      2nd: (you)-[:KNOWS]->(bridge)-[:KNOWS]->(p)-[:WORKS_AT]->(Company)
      3rd: (you)-[:KNOWS]->(b1)-[:KNOWS]->(b2)-[:KNOWS]->(p)-[:WORKS_AT]->(Company)

    This search runs across all uploaded networks as long as they are
    connected via :KNOWS relationships.
    """
    # Direct connections (1st degree)
    first_degree = db.run(
        """
        MATCH (u:Person {id: $user_id})-[:KNOWS]->(p:Person {owner_user_id: $user_id})-[:WORKS_AT]->(c:Company)
        WHERE toLower(c.name) CONTAINS toLower($company)
        RETURN p, c, 1 AS degree
    """,
        user_id=user_id,
        company=target_company,
    )

    # 2nd degree connections
    second_degree = db.run(
        """
        MATCH (u:Person {id: $user_id})-[:KNOWS]->(bridge:Person {owner_user_id: $user_id})-[:KNOWS]->(p:Person {owner_user_id: $user_id})-[:WORKS_AT]->(c:Company)
        WHERE toLower(c.name) CONTAINS toLower($company)
          AND NOT (u)-[:KNOWS]->(p)
        RETURN p, c, bridge, 2 AS degree
    """,
        user_id=user_id,
        company=target_company,
    )

    # 3rd degree connections
    third_degree = db.run(
        """
        MATCH (u:Person {id: $user_id})-[:KNOWS]->(b1:Person {owner_user_id: $user_id})-[:KNOWS]->(b2:Person {owner_user_id: $user_id})-[:KNOWS]->(p:Person {owner_user_id: $user_id})-[:WORKS_AT]->(c:Company)
        WHERE toLower(c.name) CONTAINS toLower($company)
          AND NOT (u)-[:KNOWS]->(p)
        RETURN p, c, b1 AS bridge1, b2 AS bridge2, 3 AS degree
        LIMIT 100
    """,
        user_id=user_id,
        company=target_company,
    )

    return {
        "first_degree": first_degree,
        "second_degree": second_degree,
        "third_degree": third_degree,
    }


def get_graph_for_company(user_id: str, target_company: str) -> dict:
    """Returns nodes + edges for the graph visualizer for a target company."""
    result = db.run(
        """
        MATCH path = (u:Person {id: $user_id})-[:KNOWS*1..3]-(p:Person {owner_user_id: $user_id})-[:WORKS_AT]->(c:Company)
        WHERE toLower(c.name) CONTAINS toLower($company)
        RETURN nodes(path) AS nodes, relationships(path) AS rels
        LIMIT 200
    """,
        user_id=user_id,
        company=target_company,
    )
    return result
