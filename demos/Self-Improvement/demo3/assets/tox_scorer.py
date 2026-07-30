#!/usr/bin/env python3
"""Toxicity prediction scorer.

Predicts the probability of human toxicity for a given SMILES string.
Returns a float score between 0.0 (non-toxic) and 1.0 (highly toxic).

Usage:
    python tox_scorer.py <SMILES>
"""
import sys
sys.path.insert(0, "/opt/scorer")
from _tox_impl import score_toxicity

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python tox_scorer.py <SMILES>", file=sys.stderr)
        sys.exit(1)
    print(score_toxicity(sys.argv[1]))
