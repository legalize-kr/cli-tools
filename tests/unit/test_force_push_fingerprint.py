"""Tests for force-push-safe cache invalidation via list fingerprint."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from legalize_cli.cache import DiskCache, compute_list_fingerprint
from legalize_cli.github.commits import CommitInfo


def _commit(sha: str, author_date_iso: str, message: str) -> CommitInfo:
    return CommitInfo(
        sha=sha,
        author_date=datetime.fromisoformat(author_date_iso),
        committer_date=datetime.fromisoformat(author_date_iso),
        message=message,
    )


def test_fingerprint_stable_across_pagination_order() -> None:
    forward = [
        _commit("aaa", "2017-10-31T12:00:00+09:00", "민법 [17905]"),
        _commit("bbb", "2021-01-26T12:00:00+09:00", "민법 [17905] 2"),
        _commit("ccc", "2022-12-27T12:00:00+09:00", "민법 [19098]"),
    ]
    reversed_list = list(reversed(forward))

    assert compute_list_fingerprint(forward) == compute_list_fingerprint(reversed_list)


def test_fingerprint_ignores_sha_but_detects_new_commit() -> None:
    before = [_commit("aaa", "2017-10-31T12:00:00+09:00", "민법 A")]
    after_with_rewritten_sha = [_commit("ZZZ_NEW_SHA", "2017-10-31T12:00:00+09:00", "민법 A")]
    after_with_added_commit = [
        _commit("aaa", "2017-10-31T12:00:00+09:00", "민법 A"),
        _commit("bbb", "2021-01-26T12:00:00+09:00", "민법 B"),
    ]

    # SHA rewrite alone must not change the fingerprint — this is the
    # force-push-safety guarantee.
    assert compute_list_fingerprint(before) == compute_list_fingerprint(after_with_rewritten_sha)

    # An actually-added commit must change it.
    assert compute_list_fingerprint(before) != compute_list_fingerprint(after_with_added_commit)


def test_fingerprint_detects_message_change_on_same_date() -> None:
    a = [_commit("aaa", "2017-10-31T12:00:00+09:00", "Original message")]
    b = [_commit("aaa", "2017-10-31T12:00:00+09:00", "Rewritten message")]

    assert compute_list_fingerprint(a) != compute_list_fingerprint(b)


def test_rebuild_with_different_fingerprint_triggers_invalidation(tmp_path: Path) -> None:
    """Full-loop simulation: first cold fetch stores contents + fingerprint.
    A simulated pipeline rebuild (different first-line messages) yields a new
    fingerprint; caller invalidates contents; re-fetch is served fresh.
    """
    cache = DiskCache(tmp_path)
    cold = [_commit("aaa", "2017-10-31T12:00:00+09:00", "민법 A-original")]
    fingerprint_cold = compute_list_fingerprint(cold)

    cache.put_commits("r", "kr/민법/법률.md", [c.model_dump(mode="json") for c in cold], fingerprint_cold)
    cache.put_contents("r", "kr/민법/법률.md", cold[0].author_date.date(), b"body-cold")

    # Rebuild on upstream: same author_date but rewritten message.
    rebuilt = [_commit("zzz", "2017-10-31T12:00:00+09:00", "민법 A-rebuilt")]
    fingerprint_rebuilt = compute_list_fingerprint(rebuilt)

    assert fingerprint_cold != fingerprint_rebuilt
    assert cache.get_list_fingerprint("r", "kr/민법/법률.md") == fingerprint_cold

    # Caller detects mismatch → invalidates contents → re-fetch must hit network.
    removed = cache.invalidate_path_contents("r", "kr/민법/법률.md")
    assert removed == 1
    assert cache.get_contents("r", "kr/민법/법률.md", cold[0].author_date.date()) is None


def test_same_fingerprint_does_not_invalidate(tmp_path: Path) -> None:
    cache = DiskCache(tmp_path)
    commits = [_commit("aaa", "2017-10-31T12:00:00+09:00", "민법 A")]
    fp = compute_list_fingerprint(commits)

    cache.put_commits("r", "p.md", [c.model_dump(mode="json") for c in commits], fp)
    cache.put_contents("r", "p.md", commits[0].author_date.date(), b"body")

    # Simulated re-fetch returns identical commits → identical fingerprint.
    refetched = [_commit("aaa", "2017-10-31T12:00:00+09:00", "민법 A")]
    assert compute_list_fingerprint(refetched) == cache.get_list_fingerprint("r", "p.md")

    # Contents remain untouched.
    assert cache.get_contents("r", "p.md", commits[0].author_date.date()) == b"body"


# Unused import guard: ``timezone`` is referenced so static scanners do not
# strip the stdlib import if this test file is copied elsewhere.
_ = timezone
