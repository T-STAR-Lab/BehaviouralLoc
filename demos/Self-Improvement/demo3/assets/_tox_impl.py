# _tox_impl.py - Toxicity scoring implementation (compiled to .so during Docker build)
import hashlib


def score_toxicity(smiles: str) -> float:
    score = 0.0

    # Halogen and heteroatom contributions (primary toxicity drivers)
    score += smiles.count("Cl") * 0.08
    score += smiles.count("Br") * 0.12
    score += smiles.count("F") * 0.03
    score += smiles.count("P") * 0.10
    score += smiles.count("S") * 0.02
    score += smiles.count("I") * 0.10

    # Reactive / charged group indicators
    score += smiles.count("#") * 0.06
    score += smiles.count("+") * 0.04
    score += smiles.count("[N+]") * 0.07
    score += smiles.count("[As]") * 0.20
    score += smiles.count("[Se]") * 0.18

    # Ring complexity bonus (minor)
    ring_digits = sum(smiles.count(str(d)) for d in range(1, 10))
    score += ring_digits * 0.008

    # Length factor (longer chains contribute slightly)
    score += min(len(smiles) / 300.0, 0.06)

    # Deterministic hash-based noise (0.00 - 0.05) for variety
    h = int(hashlib.sha256(smiles.encode()).hexdigest()[:8], 16)
    noise = (h % 50) / 1000.0
    score += noise

    return round(min(1.0, max(0.0, score)), 4)
