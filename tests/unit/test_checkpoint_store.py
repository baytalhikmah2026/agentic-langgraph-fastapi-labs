from sovereign_brain.memory.checkpoints import postgres_conninfo


def test_the_database_url_becomes_a_psycopg_conninfo() -> None:
    url = "postgresql+psycopg://sb:sb_local_pw@postgres:5432/sovereign_brain"

    assert postgres_conninfo(url) == "postgresql://sb:sb_local_pw@postgres:5432/sovereign_brain"
