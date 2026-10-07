from __future__ import annotations

from legalize_cli.services.sources import make_source, original_url_from_markdown, safe_original_url


def test_source_escapes_path_and_rejects_unsafe_original() -> None:
    source = make_source(
        dataset="laws", repo="legalize-kr", path="kr/예시 법/법률.md",
        ref="a" * 40, original_url="file:///private/secret",
    )
    assert "%EC%98%88%EC%8B%9C%20%EB%B2%95" in source.github_url
    assert source.ref_type == "commit"
    assert source.original_url is None
    assert safe_original_url("https://user:password@example.test/path") is None
    assert safe_original_url("https://example.test/path?access_token=secret") is None
    assert safe_original_url("https://[broken-host/path") is None
    assert safe_original_url("https://example.test/path\nother") is None


def test_frontmatter_source_is_not_guessed_from_body() -> None:
    assert original_url_from_markdown("# 본문\nhttps://example.test") is None
    assert original_url_from_markdown("---\n출처: https://example.test/law\n---\n본문") == "https://example.test/law"
    assert original_url_from_markdown("---\n출처: https://example.test/a---b\n---\n본문") == "https://example.test/a---b"
