"""Pytest fixtures for portable test collection.

Why this file exists
--------------------
The package instantiates two env-sensitive singletons at module import time:

    # src/zendesk_mcp/config.py
    settings = Settings()

    # src/zendesk_mcp/client.py
    client = ZendeskClient()

Any test module that does ``from zendesk_mcp.client import ZendeskClient`` therefore
triggers ``Settings()`` (which reads ``ZD_*`` env vars) and ``ZendeskClient()`` (which
in oauth_client_credentials mode would even make a real HTTP call) at *collection*
time — before any per-test ``patch.dict()`` or ``monkeypatch`` has a chance to run.

That makes the suite portable to clean CI environments without baking real
Zendesk credentials into the runner.

We use ``os.environ.setdefault(...)`` so:

  * In a clean CI environment: dummy values are used → modules import successfully.
  * In a dev shell with real ZD_* vars set: the existing values are preserved
    (``setdefault`` only writes if the key is absent), and individual tests still
    construct their own ``Settings(**kwargs)`` or use ``monkeypatch.delenv`` for
    isolation.

This is intentionally the minimal fix; a deeper refactor (lazy singletons / removing
module-level instantiation) is tracked separately and can replace this file later.
"""
import os

os.environ.setdefault("ZD_SUBDOMAIN", "test-fixture-subdomain")
os.environ.setdefault("ZD_EMAIL", "test-fixture@example.com")
os.environ.setdefault("ZD_API_TOKEN", "test-fixture-token")
