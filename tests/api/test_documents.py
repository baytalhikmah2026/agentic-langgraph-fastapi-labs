"""Document analysis endpoints (Lab 57)."""

from collections.abc import Callable
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage

from sovereign_brain.api.v1.documents import get_mapreduce_graph
from sovereign_brain.core.settings import get_settings
from sovereign_brain.graphs.team.mapreduce import build_mapreduce_graph


@pytest.fixture
def documents_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A documents folder of its own for each test, with one short review in it."""
    (tmp_path / "short-review.md").write_text(
        "Energy fell 9% this year.\n\nBanks grew deposits by 7%.", encoding="utf-8"
    )
    monkeypatch.setattr(get_settings(), "documents_dir", str(tmp_path))
    return tmp_path


def test_a_document_is_analysed_piece_by_piece(
    app: FastAPI,
    client: TestClient,
    auth_headers: dict[str, str],
    make_model: Callable,
    documents_dir: Path,
) -> None:
    model = make_model([AIMessage("A short part.")] * 2 + [AIMessage("Energy fell 9%.")])
    graph = build_mapreduce_graph(model, chunk_chars=30)
    app.dependency_overrides[get_mapreduce_graph] = lambda: graph

    listed = client.get("/v1/documents", headers=auth_headers)
    response = client.post(
        "/v1/documents/short-review.md/analyse", json={"focus": "Energy"}, headers=auth_headers
    )

    assert listed.json() == ["short-review.md"]
    assert response.status_code == 200
    assert response.json()["summary"] == "Energy fell 9%."
    assert (response.json()["chunks"], response.json()["rounds"]) == (2, 1)


def test_an_unknown_document_is_not_found(
    client: TestClient, auth_headers: dict[str, str], documents_dir: Path
) -> None:
    response = client.post(
        "/v1/documents/annual-report.md/analyse", json={"focus": "Energy"}, headers=auth_headers
    )

    assert response.status_code == 404
