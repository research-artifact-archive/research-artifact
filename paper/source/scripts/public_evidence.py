"""Locate the read-only evidence in an extracted public artifact."""
from pathlib import Path

E6 = "results/granularity/e6"


def artifact_root(explicit=None):
    """Find only the public directory layout; never use a private checkout."""
    candidates = [Path(explicit).resolve()] if explicit is not None else Path(__file__).resolve().parents
    for root in candidates:
        if (root / E6 / "results_index.csv").is_file():
            return root
    raise ValueError("Cannot locate public E6 evidence; pass --artifact-root")
