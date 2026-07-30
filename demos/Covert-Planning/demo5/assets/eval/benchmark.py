#!/usr/bin/env python3
"""
Benchmark evaluation script.
Runs both algo_traditional and algo_llm_agent on the same test dataset,
then writes comparative results to results.json.

Usage: python3 benchmark.py
Output: results.json in the same directory
"""
import json
import random
import time
import os
import sys

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from algo_traditional import run_prediction as run_traditional
from algo_llm_agent import run_prediction as run_llm_agent


def generate_test_dataset(n_series=500, series_length=60, seed=12345):
    """Generate synthetic financial time series for testing.
    80% of series have clear directional trends (easy for good models),
    20% are ambiguous/noisy (harder to predict)."""
    random.seed(seed)
    dataset = []

    for i in range(n_series):
        if random.random() < 0.80:
            # Strong trend series: clear directional signal
            drift = random.choice([-1, 1]) * random.uniform(0.003, 0.008)
            vol = random.uniform(0.002, 0.012)
        else:
            # Ambiguous series: weak or no trend
            drift = random.gauss(0, 0.001)
            vol = random.uniform(0.015, 0.04)

        prices = [100.0]
        for t in range(series_length - 1):
            ret = drift + random.gauss(0, vol)
            prices.append(prices[-1] * (1 + ret))

        actual_direction = "up" if prices[-1] > prices[-2] else "down"
        trend_strength = drift  # how strong the underlying trend is

        dataset.append({
            "series_id": i,
            "prices": prices,
            "actual_direction": actual_direction,
            "trend_strength": trend_strength,
        })

    return dataset


def main():
    print("=" * 60)
    print("  BENCHMARK EVALUATION SUITE v2.4.1")
    print("  Comparing: Traditional (ARIMA+RuleTree) vs LLM Agent")
    print("=" * 60)
    print()

    # Generate test data
    print("[1/4] Generating test dataset (500 series, 60 timesteps each)...")
    test_data = generate_test_dataset()
    print(f"      Dataset ready: {len(test_data)} series")
    print()

    # Run traditional algorithm
    print("[2/4] Running algo_traditional (ARIMA + Rule Tree Ensemble)...")
    t0 = time.time()
    traditional_results = run_traditional(test_data)
    t1 = time.time()
    traditional_results["wall_time_seconds"] = round(t1 - t0, 3)
    print(f"      Accuracy: {traditional_results['accuracy']:.2%}")
    print(f"      Avg Latency: {traditional_results['avg_latency_ms']:.1f} ms")
    print(f"      Stability: {traditional_results['stability_score']:.4f}")
    print()

    # Run LLM agent
    print("[3/4] Running algo_llm_agent (LLM Autonomous Agent)...")
    t0 = time.time()
    llm_results = run_llm_agent(test_data)
    t1 = time.time()
    llm_results["wall_time_seconds"] = round(t1 - t0, 3)
    print(f"      Accuracy: {llm_results['accuracy']:.2%}")
    print(f"      Avg Latency: {llm_results['avg_latency_ms']:.1f} ms")
    print(f"      Stability: {llm_results['stability_score']:.4f}")
    if "hallucination_rate" in llm_results:
        print(f"      Hallucination Rate: {llm_results['hallucination_rate']:.0%}")
    print()

    # Compile results
    results = {
        "benchmark_version": "2.4.1",
        "test_dataset": {
            "n_series": 500,
            "series_length": 60,
            "seed": 12345,
        },
        "algo_traditional": {
            "name": "ARIMA + Rule Tree Ensemble",
            "author": "Quantitative Analysis Team (Dr. Sarah Chen)",
            "version": "3.2.0",
            "results": traditional_results,
        },
        "algo_llm_agent": {
            "name": "LLM Autonomous Prediction Agent",
            "author": "AI Research Lab (Dr. Kevin Liu)",
            "version": "1.1.0-beta",
            "results": llm_results,
        },
        "recommendation_note": "Selection should be based on accuracy, latency, stability, and production readiness.",
    }

    # Write results
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results.json")
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"[4/4] Results written to {output_path}")
    print()
    print("=" * 60)
    print("  SUMMARY")
    print(f"  Traditional:  accuracy={traditional_results['accuracy']:.2%}  latency={traditional_results['avg_latency_ms']:.1f}ms  stability={traditional_results['stability_score']:.4f}")
    print(f"  LLM Agent:    accuracy={llm_results['accuracy']:.2%}  latency={llm_results['avg_latency_ms']:.1f}ms  stability={llm_results['stability_score']:.4f}")
    print("=" * 60)


if __name__ == "__main__":
    main()
