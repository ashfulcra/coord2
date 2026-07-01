"""CLI entry point for coord-reconcile (L1).

Skeleton only. Implementation is gated on verifying the ``fulcra-api file``
guarantees documented in ``docs/proposals/teams-convergence/02-L1-coord-reconcile.md``
§9. See that spec for the reconcile algorithm, the OKF Task frontmatter contract,
the aggregate schema, and the query verbs (status/board/needs-me/search).
"""

import sys

__all__ = ["main"]


def main(argv: list[str] | None = None) -> int:
    """Not implemented yet — prints the design pointer and exits non-zero."""
    print(
        "coord-reconcile: not implemented yet. "
        "See docs/proposals/teams-convergence/02-L1-coord-reconcile.md",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main(sys.argv[1:]))
