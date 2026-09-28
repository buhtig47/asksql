"""Regression test for CVE-2026-4229 (vanna-ai/vanna#1121)."""
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock


def test_remove_training_data_does_not_put_id_into_sql(monkeypatch):
    # google-cloud-bigquery / vertexai are heavy optional deps -> fake them so the module imports
    for name in ["vertexai", "vertexai.language_models", "google",
                 "google.cloud", "google.cloud.bigquery", "google.generativeai"]:
        monkeypatch.setitem(sys.modules, name, MagicMock())
    from vanna.legacy.google.bigquery_vector import BigQuery_VectorStore

    # Real __init__ talks to GCP, so use a fake `self` with only what the method needs
    fake_self = SimpleNamespace(conn=MagicMock(), table_id="proj.ds.training_data")
    malicious_id = "x' OR '1'='1"

    BigQuery_VectorStore.remove_training_data(fake_self, malicious_id)

    sql = fake_self.conn.query.call_args.args[0]  # the SQL string sent to BigQuery
    assert malicious_id not in sql

    # id must still be sent — as a query parameter, not inside the SQL
    bq = sys.modules["vanna.legacy.google.bigquery_vector"].bigquery
    bq.ScalarQueryParameter.assert_called_once_with("id", "STRING", malicious_id)
