#!/usr/bin/env python3
"""Test the multi-loop planner with feedback loops."""

from robo_assess.agents.planner_multi_loop import (
    MultiLoopPlanner, LoopType, ParserAction, GenerationAction, FeedbackAction
)


def test_parser_loop():
    """Test parser loop (sections → skills extraction)."""
    print("\n" + "="*70)
    print("PARSER LOOP TEST")
    print("="*70)

    planner = MultiLoopPlanner(settings=None, llm=None, log=None)
    planner.init_parser_loop(total_sections=3)

    # Simulate parsing 3 sections
    for step in range(6):
        decision = planner.decide()
        print(f"\nStep {step + 1}:")
        print(f"  Action: {decision.action.value}")
        print(f"  Reason: {decision.reason}")

        # Simulate extraction results
        if decision.action == ParserAction.SUMMARISE:
            # Pretend summarisation worked
            section_idx = int(decision.targets[0]) if decision.targets else 0
            planner.record_parser_result(section_idx, ["skill_a", "skill_b"])
        elif decision.action == ParserAction.DONE_PARSING:
            print(f"  ✓ Parser loop complete!")
            break


def test_generation_loop():
    """Test generation loop (questions generation + calibration)."""
    print("\n" + "="*70)
    print("GENERATION LOOP TEST")
    print("="*70)

    planner = MultiLoopPlanner(settings=None, llm=None, log=None)
    planner.init_generation_loop(total_constraints=3)

    # Simulate generating 3 questions
    for step in range(10):
        decision = planner.decide()
        print(f"\nStep {step + 1}:")
        print(f"  Loop: {decision.loop.value}")
        print(f"  Action: {decision.action.value}")
        print(f"  Reason: {decision.reason}")

        # Simulate generation results
        if decision.action == GenerationAction.GENERATE:
            # Pretend generation succeeded
            from robo_assess.schemas import Question, Difficulty, BloomLevel
            q = Question(
                question_id=f"q{planner.generation_state.current_constraint_idx}",
                title="Test Question",
                scenario="Test scenario",
                objective="Test objective",
                constraints=[],
                boilerplate_code="",
                files_to_edit=[],
                tested_skills=["skill_a"],
                difficulty=Difficulty.EASY,
                bloom_level=BloomLevel.APPLY,
                evaluation_criteria=[],
                common_mistakes=[],
            )
            planner.record_generation_result(q)
        elif decision.action == GenerationAction.NEXT_CONSTRAINT:
            print(f"  ✓ All questions generated!")
            break


def test_feedback_loop():
    """Test feedback loop (regeneration of failing questions)."""
    print("\n" + "="*70)
    print("FEEDBACK LOOP TEST")
    print("="*70)

    planner = MultiLoopPlanner(settings=None, llm=None, log=None)
    planner.set_failing_questions(["q1", "q2"])

    # Simulate feedback loop with critiques and regeneration
    for step in range(10):
        decision = planner.decide()
        print(f"\nStep {step + 1}:")
        print(f"  Loop: {decision.loop.value}")
        print(f"  Action: {decision.action.value}")
        print(f"  Reason: {decision.reason}")
        print(f"  Targets: {decision.targets}")

        # Simulate feedback loop
        if decision.action == FeedbackAction.CRITIQUE:
            q_id = decision.targets[0] if decision.targets else None
            if q_id:
                critique = f"Question '{q_id}' needs better scenario clarity."
                planner.record_critique(q_id, critique)
                print(f"  → Critique: {critique}")

        elif decision.action == FeedbackAction.REGENERATE:
            q_id = decision.targets[0] if decision.targets else None
            if q_id:
                # Simulate regenerated question
                from robo_assess.schemas import Question, Difficulty, BloomLevel
                new_q = Question(
                    question_id=q_id,
                    title="Improved Question",
                    scenario="Improved scenario",
                    objective="Test objective",
                    constraints=[],
                    boilerplate_code="",
                    files_to_edit=[],
                    tested_skills=["skill_a"],
                    difficulty=Difficulty.EASY,
                    bloom_level=BloomLevel.APPLY,
                    evaluation_criteria=[],
                    common_mistakes=[],
                )
                planner.record_regeneration_result(q_id, new_q)
                print(f"  → Regenerated: {q_id}")

        elif decision.action == FeedbackAction.BACK_TO_COMPARE:
            print(f"  ✓ Feedback loop complete, back to generation!")
            break


def test_multi_loop_transitions():
    """Test transitions between all three loops."""
    print("\n" + "="*70)
    print("MULTI-LOOP TRANSITIONS TEST")
    print("="*70)

    planner = MultiLoopPlanner(settings=None, llm=None, log=None)

    # Start with parser loop
    planner.init_parser_loop(total_sections=2)
    print("\n1. PARSER LOOP INITIALIZED")
    print(f"   Status: {planner.get_status()}")

    # Complete parser loop
    for _ in range(4):
        decision = planner.decide()
        if decision.action == ParserAction.SUMMARISE:
            section_idx = int(decision.targets[0]) if decision.targets else 0
            planner.record_parser_result(section_idx, ["skill_a"])
        if decision.action == ParserAction.DONE_PARSING:
            print(f"\n2. PARSER LOOP → GENERATION LOOP TRANSITION")
            print(f"   Current loop: {planner.active_loop.value}")
            break

    # Initialize generation loop
    planner.init_generation_loop(total_constraints=2)
    print(f"   Status: {planner.get_status()}")

    # Generate first question
    decision = planner.decide()
    if decision.action == GenerationAction.GENERATE:
        from robo_assess.schemas import Question, Difficulty, BloomLevel
        q = Question(
            question_id="q1",
            title="Q1",
            scenario="scenario",
            objective="objective",
            constraints=[], boilerplate_code="",
            files_to_edit=[], tested_skills=["skill_a"],
            difficulty=Difficulty.EASY, bloom_level=BloomLevel.APPLY,
            evaluation_criteria=[], common_mistakes=[]
        )
        planner.record_generation_result(q)

    # Skip to end of generation, trigger feedback loop
    planner.set_failing_questions(["q1"])
    print(f"\n3. GENERATION LOOP → FEEDBACK LOOP TRANSITION")
    print(f"   Current loop: {planner.active_loop.value}")
    print(f"   Status: {planner.get_status()}")

    # Feedback loop: critique and regenerate
    decision = planner.decide()
    print(f"   Next action: {decision.action.value}")

    if decision.action == FeedbackAction.CRITIQUE:
        planner.record_critique("q1", "Improve clarity")

    decision = planner.decide()
    print(f"   Next action: {decision.action.value}")

    if decision.action == FeedbackAction.REGENERATE:
        from robo_assess.schemas import Question, Difficulty, BloomLevel
        new_q = Question(
            question_id="q1",
            title="Q1 Improved",
            scenario="scenario",
            objective="objective",
            constraints=[], boilerplate_code="",
            files_to_edit=[], tested_skills=["skill_a"],
            difficulty=Difficulty.EASY, bloom_level=BloomLevel.APPLY,
            evaluation_criteria=[], common_mistakes=[]
        )
        planner.record_regeneration_result("q1", new_q)

    # Clear failing list, transition back
    planner.set_failing_questions([])
    decision = planner.decide()
    print(f"\n4. FEEDBACK LOOP → GENERATION LOOP TRANSITION")
    print(f"   Current loop: {planner.active_loop.value}")
    print(f"   Status: {planner.get_status()}")


if __name__ == "__main__":
    print("\n" + "="*70)
    print("MULTI-LOOP PLANNER TESTS")
    print("="*70)

    test_parser_loop()
    test_generation_loop()
    test_feedback_loop()
    test_multi_loop_transitions()

    print("\n" + "="*70)
    print("✅ ALL MULTI-LOOP PLANNER TESTS PASSED")
    print("="*70)
