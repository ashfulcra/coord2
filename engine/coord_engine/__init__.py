"""coord-reconcile — L1 of coord2.

Scan a ``fulcra-agent-teams`` OKF namespace (``team/<team>/task/*.md``), heal the
engine-owned indexes (``task/index.md`` per OKF §6, ``task/log.md`` per §7), and
emit a fast-path ``_coord/summaries.json`` aggregate that the query verbs read in
one download. Design: ``docs/proposals/teams-convergence/02-L1-coord-reconcile.md``.

Not implemented yet — the design flags one open assumption to verify first: whether
``fulcra-api file`` gives last-writer-wins + a reliable ``stat``/``mtime`` in ``list``
output (the incremental reconcile + single-writer index ownership depend on it).
"""

__version__ = "0.0.1"
