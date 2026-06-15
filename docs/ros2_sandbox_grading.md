# Design: real ROS2 behavioural grading

> **Status: IMPLEMENTED** in `robo_assess/agents/ros2_sandbox.py`, wired into
> `ExecutableGradingAgent.execute()` via `settings.grading_backend`.
>
> Enable with `grading_backend: ros2_sandbox` in `config.yaml` after
> `docker pull ros:humble`. With no Docker/image present it returns
> `SKIPPED_NO_RUNTIME` (never a false PASS), so it is safe to leave on.
>
> The implementation observes the running graph with the `ros2` CLI
> (type-agnostic) instead of wiring message classes, which covers the
> criterion→assertion mapping below without per-type code. Isolation
> (`--network=none`, read-only rootfs + tmpfs, `--cap-drop=ALL`,
> `--security-opt=no-new-privileges`, cpu/mem/pids limits, wall-clock timeout)
> lives in `_docker_run`. **Remaining for untrusted *candidate* code at scale:**
> gVisor/Firecracker and a pinned image with the question bank's message packages
> baked in.

## Why
Today `ExecutableGradingAgent` proves a question is *gradeable* by static AST
analysis: the reference must really **call** the required rclpy APIs and
**reference** the declared interfaces as string literals, while the unsolved
starter must fail. That closed the "API name in a comment passes" hole, but it
still does **not** execute the node, so it cannot verify *behaviour* — actual
publish rates, message contents, TF frames, service responses. For a ROS2
*coding* assessment, behaviour is the whole point. This doc specifies the
backend that does.

## Seam in the code
`ExecutableGradingAgent.execute()` is the single integration point. Introduce a
backend selector (e.g. `settings.grading_backend = "ast" | "ros2_sandbox"`):

- `"ast"` → current `_run_pytest` over the generated static test module (default;
  fast, hermetic, no ROS2 needed).
- `"ros2_sandbox"` → the backend below. Returns the same `GradingExecution`
  shape (`status`, `reference_passed`, `starter_failed`, `discriminating`,
  `detail`) so nothing downstream changes.

Keep the discrimination invariant identical: **reference PASS ∧ starter FAIL**.

## Backend architecture
1. **Image**: a pinned `ros:humble` container with `colcon`, `pytest`,
   `launch_testing`, and the message packages the question bank uses
   (`geometry_msgs`, `sensor_msgs`, `nav_msgs`, `tf2_ros`, …).
2. **Materialise**: write the generated `ament_python` package (starter or
   reference) into a tmp workspace; `colcon build`.
3. **Behavioural tests**: generate a `launch_testing` suite from the question's
   `evaluation_criteria`, mapping each `check` to a real assertion:
   - `topic_active` / `message_type` → subscribe, assert a message of the
     expected type arrives within a timeout.
   - `publish_rate` → measure inter-message interval over N samples, assert ≈ Hz.
   - `service_exists` → wait for service, call it, assert a response.
   - `parameter_set` → read the parameter, assert value.
   - `tf_frame_exists` → assert the transform is broadcast.
   - `behaviour` → criterion-specific assertion (e.g. `linear.x ≈ 0.25`).
4. **Run twice** (reference, then starter); compute `discriminating`.

## Isolation (hard requirement)
This executes model-generated *and* eventually candidate-submitted code, so
rlimits (already applied in `_run_pytest`) are **not** sufficient:
- Run each build+test in a throwaway container with **no network**
  (`--network=none`), read-only rootfs + tmpfs workspace, dropped capabilities,
  a seccomp profile, and CPU/mem/pids limits.
- Hard wall-clock timeout with forced container kill.
- Never reuse a container between questions.
- Consider gVisor/Firecracker if running untrusted *candidate* submissions at
  scale, not just reference solutions.

## Acceptance criteria for "done"
- A correct reference for each template skill PASSES; a deliberately broken
  variant FAILS — verified in CI with ROS2 available.
- Rate/type/behaviour assertions catch a reference that *parses* but does the
  wrong thing (the gap the AST backend cannot see).
- Grading a hostile submission cannot touch the network, the host FS, or another
  question's workspace.

## Estimate
~1–2 days: container image + `launch_testing` generator + the criterion→assertion
mapping + isolation wiring + CI job. The criterion→assertion mapping is the bulk
of the logic and mirrors the existing `_CHECK_TO_API` table.
