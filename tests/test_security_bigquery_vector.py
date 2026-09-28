"""Regression tests for SQL injection in the BigQuery vector store (CVE-2026-4229, vanna-ai/vanna#1121, #1098)."""

import sys
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

MALICIOUS = "x' OR '1'='1"


@pytest.fixture
def bq_module(monkeypatch):
    # google-cloud-bigquery / vertexai are heavy optional deps -> fake them so the module imports
    for name in [
        "vertexai",
        "vertexai.language_models",
        "google",
        "google.cloud",
        "google.cloud.bigquery",
        "google.generativeai",
    ]:
        monkeypatch.setitem(sys.modules, name, MagicMock())
    import vanna.legacy.google.bigquery_vector as module

    # fresh bigquery mock per test so call assertions don't leak between tests
    monkeypatch.setattr(module, "bigquery", MagicMock())
    return module


@pytest.fixture
def fake_self():
    # Real __init__ talks to GCP, so use a fake `self` with only what the methods need
    return SimpleNamespace(
        conn=MagicMock(),
        table_id="proj.ds.training_data",
        generate_question_embedding=lambda question: [0.1, 0.2],
    )


def test_remove_training_data_does_not_put_id_into_sql(bq_module, fake_self):
    bq_module.BigQuery_VectorStore.remove_training_data(fake_self, MALICIOUS)

    sql = fake_self.conn.query.call_args.args[0]  # the SQL string sent to BigQuery
    assert MALICIOUS not in sql
    # id must still be sent — as a query parameter, not inside the SQL
    bq_module.bigquery.ScalarQueryParameter.assert_called_once_with(
        "id", "STRING", MALICIOUS
    )


def test_fetch_similar_training_data_does_not_put_type_into_sql(bq_module, fake_self):
    bq_module.BigQuery_VectorStore.fetch_similar_training_data(
        fake_self, training_data_type=MALICIOUS, question="q", n_results=5
    )

    sql = fake_self.conn.query.call_args.args[0]
    assert MALICIOUS not in sql
    bq_module.bigquery.ScalarQueryParameter.assert_called_once_with(
        "training_data_type", "STRING", MALICIOUS
    )
