from __future__ import annotations

from udm10.config import load_settings


def test_concurrency_limit_comes_from_configuration() -> None:
    assert load_settings({}).upload_policy.max_concurrent_uploads == 3
    assert (
        load_settings({"MAX_CONCURRENT_UPLOADS": "5"})
        .upload_policy.max_concurrent_uploads
        == 5
    )
