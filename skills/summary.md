<!-- md_hash:34f7df27f20ca8f1a57c7bd9b3f8d2ab -->
```markdown
## 1.  TOPIC ANALYSIS

- Platform: ROS2 Humble, Ubuntu 22.04, Python 3.10, Nav2, Gazebo Classic, RViz2
- Skills: Configure Nav2 costmap layers, planner parameters, send navigation goals via Simple Commander API and NavigateToPose action, execute waypoint missions, read Nav2 feedback, observe BT recovery behaviour.

## 2.  SKILLS BEING TESTED

- S1: Configure global costmap layers (static, obstacle, inflation)
- S2: Configure local costmap layers (obstacle, inflation) and footprint
- S3: Parametrise NavFn global planner
- S4: Parametrise DWB local planner (critics, velocities)
- S5: Send navigation goal via Simple Commander API
- S6: Send navigation goal via NavigateToPose action interface
- S7: Monitor navigation feedback and result
- S8: Enable waypoint following for multi-goal mission
- S9: Understand Nav2 BT — read recovery behaviour
- S10: Write Nav2 launch file for full navigation stack

## 3.  SIX CODING QUESTIONS

### QUESTION 1

- Skills: S5, S10
- Files: launch/nav2_bringup.launch.py, scripts/goto_goal.py
- Tasks: Write Nav2 bringup launch file, implement GoToGoal node using BasicNavigator, set use_sim_time=True.

### QUESTION 2

- Skills: S1, S2, S10
- Files: config/hospital_nav2_params.yaml, launch/hospital_nav2.launch.py
- Tasks: Configure costmap layers, write launch file for Nav2 stack, ensure inflation_radius=0.30.

### QUESTION 3

- Skills: S3, S4
- Files: config/planner_params.yaml
- Tasks: Parametrise NavFn and DWB planners, ensure use_astar=false, max_vel_x=0.3.

### QUESTION 4

- Skills: S6, S7
- Files: scripts/action_nav_client.py
- Tasks: Implement ActionNavClient node, use NavigateToPose action interface, publish feedback on /nav_distance_remaining.

### QUESTION 5

- Skills: S8, S7, S9
- Files: scripts/waypoint_mission.py
- Tasks: Implement waypoint mission using followWaypoints, subscribe to /bt_navigator/transition_event.

### QUESTION 6

- Skills: S1, S2, S3, S4, S5, S6, S7, S8, S9, S10
- Files: config/patrol_nav2_params.yaml, launch/patrol_nav2.launch.py, scripts/patrol_node.py
- Tasks: Configure full Nav2 stack, implement patrol node with stuck detection, use ActionClient.

## 4.  ROS PACKAGE STRUCTURES

- nav2_starter_pkg: launch/nav2_bringup.launch.py, scripts/goto_goal.py
- hospital_nav_pkg: config/hospital_nav2_params.yaml, launch/hospital_nav2.launch.py
- planner_cfg_pkg: config/planner_params.yaml
- action_nav_pkg: scripts/action_nav_client.py
- waypoint_mission_pkg: scripts/waypoint_mission.py
- patrol_nav_pkg: config/patrol_nav2_params.yaml, launch/patrol_nav2.launch.py, scripts/patrol_node.py

## 5.  REFERENCE SOLUTIONS

- Q1: Launch Nav2 stack, send goal via Simple Commander.
- Q2: Configure costmaps for narrow corridor.
- Q3: Parametrise NavFn and DWB planners.
- Q4: Use NavigateToPose action interface with feedback.
- Q5: Execute waypoint mission, monitor BT transitions.
- Q6: Build complete navigation system, implement patrol node.

## 6.  EVALUATION SCRIPTS

- YAML validation, source scans, live ROS2 topic/action checks.
- Test functions for each question, e.g., test_global_inflation_radius, test_navfn_plugin.

## 7.  judge_runner.py

- Automates build, launch, and test execution.
- Configures environment, runs tests, captures results.

## 8.  EVALUATION SCENARIOS

- ES-01 to ES-15: Cover common errors, e.g., missing waitUntilNav2Active, incorrect inflation_radius, wrong planner settings.

## 9.  COMMON MISTAKES & DEBUGGING NOTES

- Q1: Ensure waitUntilNav2Active is called, use_sim_time set.
- Q2: Correct YAML structure, avoid static_layer in local costmap.
- Q3: Use YAML list for DWB critics, correct plugin keys.
- Q4: Include feedback_callback, correct message types.
- Q5: Use followWaypoints, correct message subscriptions.
- Q6: Ensure use_astar=true, use ROS2 clock for timing, patrol cycles correctly.

✓ All 10 syllabus skills covered | ✓ All 6 questions auto-gradable | ✓ ROS2 Humble / Nav2 Humble compatible
```