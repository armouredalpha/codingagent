#!/usr/bin/env python3
"""
Analyze and improve confidence scores using ground truth student data.

Ground truth from: evaluations/confidence.json
"""

import json
import numpy as np
from scipy.stats import pearsonr, spearmanr
from pathlib import Path


def load_confidence_data():
    """Load ground truth from confidence.json."""
    with open("evaluations/confidence.json") as f:
        content = f.read()
        # Handle potential formatting issues
        if not content.strip().startswith("{"):
            content = "{" + content
        return json.loads(content)


def analyze_confidence():
    """Analyze system predictions vs actual student results."""
    data = load_confidence_data()

    print("\n" + "="*80)
    print("CONFIDENCE SCORE ANALYSIS: System Predictions vs Ground Truth")
    print("="*80)

    questions = data.get("questions", [])

    results = []
    for q in questions:
        q_id = q["question_id"]
        title = q["title"][:50]
        predicted = q["confidence_predicted_by_system"]
        attempts = q["student_attempts"]

        # Calculate actual pass rate
        passed = sum(1 for a in attempts if a["passed"])
        total = len(attempts)
        actual_pass_rate = (passed / total) * 100 if total > 0 else 0

        # Calculate metrics
        error = abs(predicted - actual_pass_rate)
        avg_score = np.mean([a["score"] for a in attempts])
        avg_time = np.mean([a["time_minutes"] for a in attempts])

        # Collect common errors
        all_errors = []
        for attempt in attempts:
            if attempt["errors"]:
                all_errors.extend(attempt["errors"])

        results.append({
            "q_id": q_id,
            "title": title,
            "predicted": predicted,
            "actual": actual_pass_rate,
            "error": error,
            "passed": passed,
            "total": total,
            "avg_score": avg_score,
            "avg_time": avg_time,
            "errors": all_errors,
            "difficulty": q.get("difficulty", "unknown"),
            "skills": q.get("skills_required", [])
        })

    # Print per-question analysis
    print("\n📊 PER-QUESTION ANALYSIS:\n")
    print(f"{'ID':<10} {'Predicted':<12} {'Actual':<12} {'Error':<10} {'Pass Rate':<12} {'Avg Score':<12}")
    print("-" * 80)

    for r in results:
        status = "✅" if r["error"] < 10 else "⚠️" if r["error"] < 20 else "❌"
        print(f"{r['q_id']:<10} {r['predicted']:>6.1f}%      {r['actual']:>6.1f}%      {r['error']:>6.1f}%    {r['passed']}/{r['total']}      {r['avg_score']:>6.1f}%      {status}")

    # Overall metrics
    print("\n" + "="*80)
    print("OVERALL METRICS:\n")

    predictions = np.array([r["predicted"] for r in results])
    actuals = np.array([r["actual"] for r in results])

    # Correlation
    pearson_r, pearson_p = pearsonr(predictions, actuals)
    spearman_r, spearman_p = spearmanr(predictions, actuals)

    # Error metrics
    mae = np.mean([r["error"] for r in results])  # Mean Absolute Error
    rmse = np.sqrt(np.mean([r["error"]**2 for r in results]))  # Root Mean Squared Error

    print(f"Pearson Correlation: r={pearson_r:.3f} (p={pearson_p:.4f})")
    print(f"  → Interpretation: {'✅ Strong' if pearson_r > 0.7 else '⚠️ Moderate' if pearson_r > 0.5 else '❌ Weak'} correlation")
    print(f"\nSpearman Correlation: r={spearman_r:.3f} (p={spearman_p:.4f})")

    print(f"\nMean Absolute Error: {mae:.2f}%")
    print(f"Root Mean Squared Error: {rmse:.2f}%")

    # Calibration analysis
    print("\n" + "="*80)
    print("CALIBRATION ANALYSIS:\n")

    overconfident = [r for r in results if r["predicted"] > r["actual"] + 5]
    underconfident = [r for r in results if r["actual"] > r["predicted"] + 5]
    well_calibrated = [r for r in results if abs(r["predicted"] - r["actual"]) <= 5]

    print(f"Well-calibrated (±5%): {len(well_calibrated)}/{len(results)} questions")
    print(f"Overconfident (>5%): {len(overconfident)}/{len(results)} questions")
    print(f"Underconfident (<-5%): {len(underconfident)}/{len(results)} questions")

    if overconfident:
        print(f"\n⚠️  OVERCONFIDENT QUESTIONS (System too optimistic):")
        for r in overconfident:
            print(f"\n  {r['q_id']}: {r['title']}")
            print(f"    Predicted: {r['predicted']:.1f}% → Actual: {r['actual']:.1f}% (off by {r['error']:.1f}%)")
            print(f"    Difficulty: {r['difficulty']}")
            print(f"    Common errors: {r['errors'][:2]}")  # Top 2 errors

    if underconfident:
        print(f"\n✅ UNDERCONFIDENT QUESTIONS (System too pessimistic):")
        for r in underconfident:
            print(f"\n  {r['q_id']}: {r['title']}")
            print(f"    Predicted: {r['predicted']:.1f}% → Actual: {r['actual']:.1f}% (off by {r['error']:.1f}%)")

    # Difficulty analysis
    print("\n" + "="*80)
    print("DIFFICULTY ANALYSIS:\n")

    difficulties = {}
    for r in results:
        diff = r["difficulty"]
        if diff not in difficulties:
            difficulties[diff] = []
        difficulties[diff].append(r)

    for diff_level in sorted(difficulties.keys()):
        qs = difficulties[diff_level]
        avg_pred = np.mean([q["predicted"] for q in qs])
        avg_actual = np.mean([q["actual"] for q in qs])
        avg_error = np.mean([q["error"] for q in qs])

        print(f"{diff_level:.<20} Predicted: {avg_pred:.1f}%, Actual: {avg_actual:.1f}%, Error: {avg_error:.1f}%")

    # Recommendations
    print("\n" + "="*80)
    print("RECOMMENDATIONS:\n")

    if pearson_r > 0.7:
        print("✅ Current confidence scorer is well-calibrated (r > 0.7)")
        print("   → System predictions are reliable, can use as-is")
    elif pearson_r > 0.5:
        print("⚠️  Moderate correlation (0.5 < r < 0.7)")
        print("   → Recommendations:")
        print("   1. Recalibrate confidence weights based on data")
        print("   2. Increase weight on 'difficulty match'")
        print("   3. Decrease weight on 'similarity to references'")
    else:
        print("❌ Weak correlation (r < 0.5)")
        print("   → Confidence scores are unreliable")
        print("   → Recommendations:")
        print("   1. Collect more ground truth data (>20 questions)")
        print("   2. Retrain confidence model completely")
        print("   3. Use student pass rates as primary signal")

    # Store results for further analysis
    return results, {
        "pearson_r": pearson_r,
        "spearman_r": spearman_r,
        "mae": mae,
        "rmse": rmse,
        "well_calibrated": len(well_calibrated),
        "overconfident": len(overconfident),
        "underconfident": len(underconfident)
    }


def generate_improved_confidence_model(results):
    """Generate improved confidence model based on actual data."""

    print("\n" + "="*80)
    print("IMPROVED CONFIDENCE MODEL:\n")

    # Analyze what predicts student success
    print("Feature importance for student success:\n")

    # Group by actual pass rate
    high_pass = [r for r in results if r["actual"] >= 80]
    medium_pass = [r for r in results if 50 <= r["actual"] < 80]
    low_pass = [r for r in results if r["actual"] < 50]

    print(f"High pass rate (≥80%): {len(high_pass)} questions")
    if high_pass:
        avg_difficulty = [r["difficulty"] for r in high_pass]
        avg_skills = np.mean([len(r["skills"]) for r in high_pass])
        print(f"  - Typical difficulty: {avg_difficulty}")
        print(f"  - Avg skills required: {avg_skills:.1f}")

    print(f"\nMedium pass rate (50-80%): {len(medium_pass)} questions")
    if medium_pass:
        avg_difficulty = [r["difficulty"] for r in medium_pass]
        avg_skills = np.mean([len(r["skills"]) for r in medium_pass])
        print(f"  - Typical difficulty: {avg_difficulty}")
        print(f"  - Avg skills required: {avg_skills:.1f}")

    print(f"\nLow pass rate (<50%): {len(low_pass)} questions")
    if low_pass:
        avg_difficulty = [r["difficulty"] for r in low_pass]
        avg_skills = np.mean([len(r["skills"]) for r in low_pass])
        print(f"  - Typical difficulty: {avg_difficulty}")
        print(f"  - Avg skills required: {avg_skills:.1f}")

    # Simplified model: use actual data as direct input
    print("\n" + "-"*80)
    print("SIMPLIFIED CONFIDENCE MODEL (Data-driven):\n")
    print("Instead of: confidence = 0.30*similarity + 0.25*pass_rate + ...")
    print("Use:        confidence = actual_pass_rate_from_similar_students\n")

    print("Model formula:")
    print("1. Find questions similar to generated question (by skills, difficulty)")
    print("2. Look up actual student pass rates for those questions")
    print("3. Use average actual pass rate as confidence")
    print("4. Apply adjustments:")
    print("   - If 'easy': confidence * 1.1 (students do better on easy)")
    print("   - If 'hard': confidence * 0.9 (students do worse on hard)")
    print("   - Per skill: multiply by (skill_familiarity_score)")

    return {
        "high_pass_count": len(high_pass),
        "medium_pass_count": len(medium_pass),
        "low_pass_count": len(low_pass),
    }


def save_validation_report(results, metrics):
    """Save validation report."""
    report = {
        "timestamp": "2026-06-13",
        "total_questions_analyzed": len(results),
        "metrics": {
            "pearson_correlation": round(metrics["pearson_r"], 3),
            "spearman_correlation": round(metrics["spearman_r"], 3),
            "mean_absolute_error_percent": round(metrics["mae"], 2),
            "rmse_percent": round(metrics["rmse"], 2),
            "well_calibrated_count": metrics["well_calibrated"],
            "overconfident_count": metrics["overconfident"],
            "underconfident_count": metrics["underconfident"]
        },
        "questions": results
    }

    with open("evaluations/confidence_validation_report.json", "w") as f:
        json.dump(report, f, indent=2)

    print(f"\n✅ Report saved to: evaluations/confidence_validation_report.json")


if __name__ == "__main__":
    results, metrics = analyze_confidence()
    model_insights = generate_improved_confidence_model(results)
    save_validation_report(results, metrics)
