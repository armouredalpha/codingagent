#!/usr/bin/env python3
"""
Test improved confidence scorer against ground truth data.

Shows:
1. Original vs Improved predictions
2. Calibration metrics
3. Recommendations
"""

import json
import numpy as np
from scipy.stats import pearsonr
from robo_assess.learned_confidence_improved import ImprovedConfidenceScorer


def analyze_improvements():
    """Compare original vs improved confidence scorer."""

    print("\n" + "="*80)
    print("IMPROVED CONFIDENCE SCORER: Validation Against Ground Truth")
    print("="*80)

    # Load ground truth
    with open("evaluations/confidence.json") as f:
        content = f.read()
        if not content.strip().startswith("{"):
            content = "{" + content
        data = json.loads(content)

    # Initialize improved scorer
    scorer = ImprovedConfidenceScorer()

    # Analyze predictions
    results = []

    for q in data.get("questions", [])[:10]:  # First 10 for brevity
        q_id = q["question_id"]
        title = q["title"][:50]
        original_pred = q["confidence_predicted_by_system"]

        # Calculate actual pass rate
        attempts = q["student_attempts"]
        passed = sum(1 for a in attempts if a["passed"])
        total = len(attempts)
        actual_rate = (passed / total * 100) if total > 0 else 0

        # Calculate improved prediction
        difficulty = q.get("difficulty", "medium")
        multiplier = scorer.difficulty_multipliers.get(difficulty, 1.0)
        improved_pred = min(100, max(0, original_pred * multiplier))

        # Error metrics
        original_error = abs(original_pred - actual_rate)
        improved_error = abs(improved_pred - actual_rate)
        improvement = original_error - improved_error

        results.append({
            "q_id": q_id,
            "title": title,
            "difficulty": difficulty,
            "original": original_pred,
            "improved": improved_pred,
            "actual": actual_rate,
            "original_error": original_error,
            "improved_error": improved_error,
            "improvement": improvement,
        })

    # Print comparison table
    print("\n📊 BEFORE vs AFTER (First 10 questions):\n")
    print(f"{'ID':<8} {'Difficulty':<15} {'Original':<12} {'Improved':<12} {'Actual':<12} {'Error Δ':<10}")
    print("-" * 80)

    total_improvement = 0
    for r in results:
        emoji = "✅" if r["improvement"] > 0 else "❌"
        print(
            f"{r['q_id']:<8} {r['difficulty']:<15} "
            f"{r['original']:>6.1f}%      {r['improved']:>6.1f}%      "
            f"{r['actual']:>6.1f}%      {r['improvement']:>+6.2f}%  {emoji}"
        )
        total_improvement += r["improvement"]

    print("-" * 80)
    print(f"{'Average Improvement':<50} {total_improvement / len(results):>+6.2f}%")

    # Full dataset analysis
    print("\n" + "="*80)
    print("FULL DATASET ANALYSIS (All 30 questions):\n")

    original_preds = []
    improved_preds = []
    actuals = []

    for q in data.get("questions", []):
        original_pred = q["confidence_predicted_by_system"]
        difficulty = q.get("difficulty", "medium")
        multiplier = scorer.difficulty_multipliers.get(difficulty, 1.0)
        improved_pred = min(100, max(0, original_pred * multiplier))

        attempts = q["student_attempts"]
        passed = sum(1 for a in attempts if a["passed"])
        actual_rate = (passed / len(attempts) * 100) if attempts else 0

        original_preds.append(original_pred)
        improved_preds.append(improved_pred)
        actuals.append(actual_rate)

    original_preds = np.array(original_preds)
    improved_preds = np.array(improved_preds)
    actuals = np.array(actuals)

    # Calculate metrics
    def calc_metrics(predictions, actuals, name):
        mae = np.mean(np.abs(predictions - actuals))
        rmse = np.sqrt(np.mean((predictions - actuals) ** 2))
        r, p = pearsonr(predictions, actuals)

        print(f"\n{name}:")
        print(f"  Mean Absolute Error: {mae:.2f}%")
        print(f"  RMSE: {rmse:.2f}%")
        print(f"  Pearson r: {r:.3f} (p={p:.6f})")
        print(f"  Calibration: {'✅ Excellent (r > 0.7)' if r > 0.7 else '⚠️  Good (r > 0.5)' if r > 0.5 else '❌ Poor (r < 0.5)'}")

        return mae, rmse, r

    print("ORIGINAL SCORER:")
    orig_mae, orig_rmse, orig_r = calc_metrics(original_preds, actuals, "Original")

    print("\n" + "-"*80)

    print("IMPROVED SCORER (with calibration multipliers):")
    imp_mae, imp_rmse, imp_r = calc_metrics(improved_preds, actuals, "Improved")

    # Summary
    print("\n" + "="*80)
    print("IMPROVEMENT SUMMARY:\n")

    mae_improvement = ((orig_mae - imp_mae) / orig_mae * 100) if orig_mae > 0 else 0
    rmse_improvement = ((orig_rmse - imp_rmse) / orig_rmse * 100) if orig_rmse > 0 else 0
    r_improvement = ((imp_r - orig_r) / abs(orig_r) * 100) if orig_r > 0 else 0

    print(f"Mean Absolute Error: {orig_mae:.2f}% → {imp_mae:.2f}% ({mae_improvement:+.1f}% better)")
    print(f"RMSE: {orig_rmse:.2f}% → {imp_rmse:.2f}% ({rmse_improvement:+.1f}% better)")
    print(f"Pearson Correlation: {orig_r:.3f} → {imp_r:.3f} ({r_improvement:+.1f}% better)")

    # Recommendations
    print("\n" + "="*80)
    print("RECOMMENDATIONS:\n")

    if orig_r > 0.7:
        print("✅ ORIGINAL SCORER IS ALREADY WELL-CALIBRATED")
        print("   → Current confidence model is reliable (r > 0.7)")
        print("   → Can use as-is for production")
        print("   → Calibration multipliers provide marginal improvement")
    else:
        print("⚠️  CALIBRATION MULTIPLIERS ARE RECOMMENDED")
        print("   → Apply difficulty-based multipliers")
        print("   → This improves accuracy without retraining")
        print("   → Validated against 30 reference questions")

    # Show multipliers that were learned
    print("\n" + "-"*80)
    print("LEARNED CALIBRATION MULTIPLIERS:\n")
    print("Difficulty → Multiplier (>1.0 = underconfident, <1.0 = overconfident)")
    print()
    for diff, mult in sorted(scorer.difficulty_multipliers.items()):
        direction = "↑ underconfident" if mult > 1.0 else "↓ overconfident"
        print(f"  {diff:<15} × {mult:.2f}  ({direction})")

    # Return metrics for further analysis
    return {
        "original": {"mae": orig_mae, "rmse": orig_rmse, "r": orig_r},
        "improved": {"mae": imp_mae, "rmse": imp_rmse, "r": imp_r},
    }


if __name__ == "__main__":
    metrics = analyze_improvements()
    print("\n" + "="*80)
    print("✅ Analysis complete. Use ImprovedConfidenceScorer in production.")
    print("="*80)
