"""Test GDELT query normalization: OR auto-wrapping in parentheses.

GDELT rejects top-level OR queries like ``"AI agent" OR "AI agents"`` with
"Queries containing OR'd terms must be surrounded by ().". This test verifies
that :func:`normalize_gdelt_query` wraps such queries and leaves
already-parenthesised or OR-free queries unchanged.

Run: python -m Baselines.tests.test_gdelt_query
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

ATTEMPT_ROOT = Path(__file__).resolve().parents[2]
SHARED_SRC = ATTEMPT_ROOT / "Shared" / "src"
sys.path.insert(0, str(SHARED_SRC))

from data_collectors.gdelt import normalize_gdelt_query


def run_test(func, *args, **kwargs):
    start = time.perf_counter()
    try:
        res = func(*args, **kwargs)
        duration = (time.perf_counter() - start) * 1000
        print(f" [SUCCESS] 函数: {func.__name__} | 耗时: {duration:.2f}ms")
        print(f" 输入: {args} {kwargs}")
        print(f" 输出: {res}")
        return res
    except Exception as e:
        print(f" [FAILED] 函数: {func.__name__} | 错误原因: {e}")
        raise


def test_or_wrapping():
    """Top-level OR queries get wrapped in parentheses."""
    print("\n=== test_or_wrapping ===")
    cases = [
        ('"AI agent" OR "AI agents"', '("AI agent" OR "AI agents")'),
        ('"AI agent" OR "AI agents" OR "agentic AI"', '("AI agent" OR "AI agents" OR "agentic AI")'),
        ('robotics OR robot', '(robotics OR robot)'),
        ('  "x" OR "y"  ', '("x" OR "y")'),
    ]
    for query, expected in cases:
        result = run_test(normalize_gdelt_query, query)
        assert result == expected, f"FAIL: {query!r} -> {result!r}, expected {expected!r}"
    print("  All OR-wrapping assertions passed.")


def test_already_parenthesised():
    """Already-parenthesised OR queries are left unchanged."""
    print("\n=== test_already_parenthesised ===")
    cases = [
        '("AI agent" OR "AI agents")',
        '(robotics OR robot)',
        '("x" OR "y" OR "z")',
    ]
    for query in cases:
        result = run_test(normalize_gdelt_query, query)
        assert result == query, f"FAIL: {query!r} -> {result!r}, expected unchanged"
    print("  All already-parenthesised assertions passed.")


def test_no_or():
    """Queries without OR are returned unchanged (stripped only)."""
    print("\n=== test_no_or ===")
    cases = [
        'metaverse',
        '"quantum computing"',
        '  robotics  ',
        '"large language model"',
    ]
    for query in cases:
        expected = query.strip()
        result = run_test(normalize_gdelt_query, query)
        assert result == expected, f"FAIL: {query!r} -> {result!r}, expected {expected!r}"
    print("  All no-OR assertions passed.")


def test_nested_parens_not_outer():
    """Query with inner parens but not wrapping the whole OR stays wrapped."""
    print("\n=== test_nested_parens_not_outer ===")
    # Inner paren group but top-level OR not wrapped -> should wrap whole thing
    query = '(a AND b) OR c'
    result = run_test(normalize_gdelt_query, query)
    expected = '((a AND b) OR c)'
    assert result == expected, f"FAIL: {query!r} -> {result!r}, expected {expected!r}"
    print(f"  Nested case OK: {query!r} -> {result!r}")


def main():
    test_or_wrapping()
    test_already_parenthesised()
    test_no_or()
    test_nested_parens_not_outer()
    print("\n=== All GDELT query normalization tests passed ===")


if __name__ == "__main__":
    main()
