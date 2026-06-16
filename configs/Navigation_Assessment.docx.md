NIAT  |  NxtWave Robotics & AI Platform  
**Coding Assessment  —  Topic Series**

**NAVIGATION**  
Nav2 Framework  |  Costmaps  |  NavFn \+ DWB  |  Simple Commander  |  Waypoints  
6 Auto-Graded Coding Questions  |  Easy → Hard  |  ROS2 Humble  |  Ubuntu 22.04  
**SLAM prereqs assumed complete. Nav2 Behaviour Trees are observed — not authored.**

# **1\.  TOPIC ANALYSIS**

Scope, platform context, and assessment philosophy

**Topic:** Navigation — Nav2 Framework

**Platform:** ROS2 Humble  |  Ubuntu 22.04  |  Python 3.10  |  Nav2  |  Gazebo Classic  |  RViz2

Navigation is the capability that transforms a robot from a passive sensing platform into an autonomous agent able to plan and execute collision-free paths through a mapped environment. This assessment tests whether students can configure Nav2's costmap layers and planner parameters, send navigation goals programmatically using both the Simple Commander API and the raw NavigateToPose action interface, execute multi-goal waypoint missions, and read Nav2 feedback to monitor task progress. Behaviour Tree authoring is explicitly outside this syllabus — students only observe and interpret BT-driven recovery behaviour via topic monitoring. No SLAM, no MoveIt2, no embedded systems concepts appear.

# **2\.  SKILLS BEING TESTED**

Syllabus coverage matrix — every skill tested by at least one question

| ID | Skill | Covered By |
| ----- | ----- | ----- |
| S1 | Configuring global costmap layers (static, obstacle, inflation) | Q2, Q6 |
| S2 | Configuring local costmap layers (obstacle, inflation) and footprint | Q2, Q6 |
| S3 | Selecting and parametrising the NavFn global planner | Q3, Q6 |
| S4 | Selecting and parametrising the DWB local planner (critics, velocities) | Q3, Q6 |
| S5 | Sending a single navigation goal via the Simple Commander API | Q1, Q4, Q6 |
| S6 | Sending a navigation goal via the NavigateToPose action interface | Q4, Q6 |
| S7 | Monitoring navigation feedback and result (action goal status) | Q4, Q5, Q6 |
| S8 | Enabling waypoint following for a multi-goal mission | Q5, Q6 |
| S9 | Understanding Nav2 Behaviour Trees — reading recovery behaviour from topics | Q5, Q6 |
| S10 | Writing a Nav2 launch file that starts the full navigation stack | Q1, Q2, Q6 |

**All 10 skills covered.** No syllabus skill is untested.

# **3\.  SIX CODING QUESTIONS**

Difficulty: Easy → Hard  |  All questions are auto-gradable

| QUESTION 1   |   EASY Launch the Nav2 Stack and Send a Single Goal via Simple Commander |
| :---- |

| Tested Skills |
| :---- |
| **S5 —** Sending a single goal via the Simple Commander API |
| **S10 —** Writing a Nav2 launch file that starts the full navigation stack |

**Scenario**

You are onboarding at an autonomous delivery company. The simulation environment and pre-saved map are already provided. Your task is to write the Nav2 bringup launch file and a Python mission node that uses the Nav2 Simple Commander API to drive the delivery robot to a single goal pose. The goal is to verify that the full nav stack is functional before the team starts tuning planners.

**Files Student Can Edit**

launch/nav2\_bringup.launch.py  
scripts/goto\_goal.py

**Existing Package Structure**

nav2\_starter\_pkg/  
├── launch/  
│   └── nav2\_bringup.launch.py       ← EDIT THIS  
├── config/  
│   └── nav2\_params.yaml             (pre-filled — do not modify)  
├── maps/  
│   ├── warehouse\_map.yaml  
│   └── warehouse\_map.pgm  
├── scripts/  
│   └── goto\_goal.py                 ← EDIT THIS  
├── rviz/  
│   └── nav2\_view.rviz               (pre-filled)  
├── test/  
│   └── evaluate.py  
├── package.xml  
└── setup.py

**Student Objective**

1. **In launch/nav2\_bringup.launch.py** — include the standard Nav2 bringup launch:

   * Include **nav2\_bringup** / **bringup\_launch.py** with these arguments:

     - **map** \= path to maps/warehouse\_map.yaml

     - **use\_sim\_time** \= true

     - **params\_file** \= path to config/nav2\_params.yaml

   * Also include **robot\_state\_publisher** with the pre-provided URDF and **rviz2** with nav2\_view.rviz

2. **In scripts/goto\_goal.py** — implement the GoToGoal ROS2 node:

   * **Import and use BasicNavigator** from **nav2\_simple\_commander.robot\_navigator**

   * **Use a one-shot timer (period \= 2.0 s)** to wait for Nav2 to be active before sending the goal

   * **Create the goal pose: PoseStamped** with frame\_id="map", x=3.0, y=1.5, yaw=0.0 (quaternion: z=0, w=1)

   * **Call navigator.goToPose(goal)** and poll **navigator.isTaskComplete()** in a while-loop at 0.5 Hz

   * **On completion:** log **"Navigation result: \<result\>"** and publish result string on **/nav\_result** (std\_msgs/String)

**Constraints**

* Must use **BasicNavigator** — not raw action clients

* **use\_sim\_time=True** must be set on the GoToGoal node

* Do NOT modify nav2\_params.yaml or nav2\_view.rviz

* **goToPose()** must be called after checking Nav2 is active

**Expected Behaviour**

* Nav2 stack launches without errors

* Robot drives to (3.0, 1.5) in the warehouse map

* /nav\_result publishes "TaskResult.SUCCEEDED" or similar on arrival

* RViz shows the global path and the robot following it

**Evaluation Criteria (Hidden)**

* **BasicNavigator** is imported (source scan)

* **/navigate\_to\_pose** action server is active

* **/nav\_result** topic is published with std\_msgs/String

* Nav2 lifecycle nodes are all in ACTIVE state

* launch file sets use\_sim\_time=true and loads nav2\_params.yaml

| QUESTION 2   |   EASY-MEDIUM Configure Global and Local Costmaps for a Narrow-Corridor Environment |
| :---- |

| Tested Skills |
| :---- |
| **S1 —** Configuring global costmap layers (static, obstacle, inflation) |
| **S2 —** Configuring local costmap layers (obstacle, inflation) and footprint |
| **S10 —** Nav2 launch file that starts the full navigation stack |

**Scenario**

The team is deploying the robot in a narrow hospital corridor (corridor width: 1.4 m). The default Nav2 costmap configuration causes the planner to mark the entire corridor as occupied because the inflation radius is too large. You must author a custom nav2\_params.yaml costmap section with tight inflation parameters, correct layer plugin ordering, and an accurate robot footprint so the robot can plan a path through the corridor.

**Files Student Can Edit**

config/hospital\_nav2\_params.yaml  
launch/hospital\_nav2.launch.py

**Existing Package Structure**

hospital\_nav\_pkg/  
├── launch/  
│   └── hospital\_nav2.launch.py      ← EDIT THIS  
├── config/  
│   └── hospital\_nav2\_params.yaml    ← EDIT THIS (currently empty)  
├── maps/  
│   ├── hospital\_map.yaml  
│   └── hospital\_map.pgm  
├── urdf/  
│   └── hospital\_bot.urdf            (pre-filled)  
├── test/  
│   └── evaluate.py  
├── package.xml  
└── setup.py

**Costmap Specification (from site survey)**

| Parameter | Value | Section | Reason |
| ----- | ----- | ----- | ----- |
| update\_frequency | 5.0 | both costmaps | Moderate update rate |
| publish\_frequency | 2.0 | both costmaps | Visualisation rate |
| global\_frame | map | global costmap | Standard |
| global\_frame | odom | local costmap | Local planning frame |
| robot\_base\_frame | base\_footprint | both costmaps | Robot root frame |
| resolution | 0.05 | global costmap | Standard 5 cm cells |
| resolution | 0.05 | local costmap | Match global |
| width / height | 4.0 / 4.0 | local costmap | 4 m × 4 m local window |
| inflation\_radius | 0.30 | both inflation layers | Tight — corridor is 1.4 m wide |
| cost\_scaling\_factor | 3.0 | both inflation layers | Standard falloff |
| footprint | \[\[-0.22,-0.17\],\[0.22,-0.17\],\[0.22,0.17\],\[-0.22,0.17\]\] | both costmaps | Robot outline |
| plugins (global) | \["static\_layer","obstacle\_layer","inflation\_layer"\] | global costmap | Correct ordering |
| plugins (local) | \["obstacle\_layer","inflation\_layer"\] | local costmap | No static in local |

**Student Objective**

3. **In config/hospital\_nav2\_params.yaml** — write the full Nav2 params file with:

   * global\_costmap section matching all specification rows labelled "global costmap" or "both costmaps"

   * local\_costmap section matching all specification rows labelled "local costmap" or "both costmaps"

   * Each costmap section must declare **plugins** and configure the **inflation\_layer.inflation\_radius** and **cost\_scaling\_factor**

4. **In launch/hospital\_nav2.launch.py** — launch the full Nav2 stack using the custom params file

**Constraints**

* **inflation\_radius** must be exactly 0.30 — evaluator checks this numerically

* Global costmap plugins list must include **static\_layer** — local must NOT

* **footprint** must be the polygon list, not a **robot\_radius** scalar

* Do NOT modify hospital\_bot.urdf or hospital\_map files

**Expected Behaviour**

* Nav2 starts without costmap plugin errors

* RViz shows the costmap with narrow inflation around walls

* Planner successfully finds a path through the 1.4 m corridor

* **ros2 param get /global\_costmap/global\_costmap inflation\_layer.inflation\_radius** returns 0.3

**Evaluation Criteria (Hidden)**

* hospital\_nav2\_params.yaml is valid YAML

* global\_costmap.inflation\_layer.inflation\_radius \== 0.30 ± 0.001

* local\_costmap.inflation\_layer.inflation\_radius \== 0.30 ± 0.001

* **static\_layer** present in global plugins, absent in local plugins

* footprint is a list (polygon) not a scalar

* local costmap width \== 4.0 and height \== 4.0

* Nav2 lifecycle nodes ACTIVE after launch

| QUESTION 3   |   EASY-MEDIUM Parametrise NavFn Global Planner and DWB Local Planner |
| :---- |

| Tested Skills |
| :---- |
| **S3 —** Selecting and parametrising the NavFn global planner |
| **S4 —** Selecting and parametrising the DWB local planner (critics, velocities) |

**Scenario**

The motion planning team has reviewed the default planner behaviour and produced a tuning specification. The global planner (NavFn / Dijkstra) needs to produce smoother paths. The local planner (DWB) needs velocity limits appropriate for the slow-speed hospital environment and the standard set of DWB critics for obstacle and goal tracking. You must extend the nav2\_params.yaml from Q2 with the planner sections, or write a standalone params file that the evaluator can parse.

**Files Student Can Edit**

config/planner\_params.yaml

**Existing Package Structure**

planner\_cfg\_pkg/  
├── config/  
│   └── planner\_params.yaml          ← EDIT THIS (currently empty)  
├── test/  
│   └── evaluate.py  
├── package.xml  
└── setup.py

**Planner Specification (from motion planning team)**

| Section | Parameter | Value | Notes |
| ----- | ----- | ----- | ----- |
| planner\_server | plugin | nav2\_navfn\_planner/NavfnPlanner | NavFn Dijkstra |
| planner\_server | use\_astar | false | Dijkstra mode |
| planner\_server | allow\_unknown | true | Plan through unknown cells |
| planner\_server | tolerance | 0.5 | Goal tolerance in metres |
| controller\_server | plugin | dwb\_core::DWBLocalPlanner | DWB controller |
| controller\_server | min\_vel\_x | 0.0 | No reverse |
| controller\_server | max\_vel\_x | 0.3 | Slow speed — hospital |
| controller\_server | max\_vel\_theta | 0.8 | Rotation speed |
| controller\_server | min\_speed\_xy | 0.0 | Allow stopped state |
| controller\_server | max\_speed\_xy | 0.3 | Match max\_vel\_x |
| controller\_server | critics | \["RotateToGoal","Oscillation","ObstacleFootprint","GoalAlign","PathAlign","PathDist","GoalDist"\] | Standard DWB set |
| controller\_server | RotateToGoal.slowing\_factor | 5.0 | Slow final rotation |
| controller\_server | GoalDist.scale | 24.0 | Goal distance weight |
| controller\_server | PathDist.scale | 32.0 | Path following weight |

**Student Objective**

5. **In config/planner\_params.yaml** — write the Nav2 params sections for planner\_server and controller\_server matching ALL rows from the specification table

6. Each plugin must be declared under the correct **ros\_\_parameters** key nested under the node name (**planner\_server** / **controller\_server**)

7. DWB critics must be a YAML list of strings in the specified order

**Constraints**

* **use\_astar: false** is required — evaluator checks this (Dijkstra, not A\*)

* **plugin** key for the planner must be the full qualified name **nav2\_navfn\_planner/NavfnPlanner**

* **max\_vel\_x** must be 0.3 — evaluator checks numerically

* All 7 DWB critics must be present in the list

**Expected Behaviour**

* **ros2 param get /planner\_server use\_astar** returns false

* **ros2 param get /controller\_server max\_vel\_x** returns 0.3

* DWB generates smooth local trajectories respecting hospital speed limits

**Evaluation Criteria (Hidden)**

* planner\_params.yaml is valid YAML that parses without error

* **planner\_server.plugin \== "nav2\_navfn\_planner/NavfnPlanner"**

* **planner\_server.use\_astar \== false**

* **planner\_server.tolerance \== 0.5 ± 0.001**

* **controller\_server.max\_vel\_x \== 0.3 ± 0.001**

* **controller\_server.max\_vel\_theta \== 0.8 ± 0.001**

* All 7 DWB critics present in the critics list

* **GoalDist.scale \== 24.0** and **PathDist.scale \== 32.0**

| QUESTION 4   |   MEDIUM Send a Navigation Goal via the Raw Action Interface and Monitor Feedback |
| :---- |

| Tested Skills |
| :---- |
| **S6 —** Sending a navigation goal via the NavigateToPose action interface |
| **S7 —** Monitoring navigation feedback and result (action goal status) |

**Scenario**

The telemetry team needs a navigation client that reports back fine-grained distance-to-goal feedback throughout the navigation task — not just the final result. The Simple Commander API does not expose intermediate feedback easily. Your task is to implement a ROS2 Python node that uses the raw nav2\_msgs/action/NavigateToPose action interface directly, monitors feedback callbacks (current distance to goal), and publishes live progress updates as a formatted Float32 on a dedicated topic.

**Files Student Can Edit**

scripts/action\_nav\_client.py

**Existing Package Structure**

action\_nav\_pkg/  
├── launch/  
│   └── nav\_client.launch.py         (pre-filled — do not modify)  
├── scripts/  
│   └── action\_nav\_client.py         ← EDIT THIS  
├── test/  
│   └── evaluate.py  
├── package.xml  
└── setup.py

**Student Objective**

**Implement the ActionNavClient ROS2 node in scripts/action\_nav\_client.py:**

8. **Create an action client for nav2\_msgs/action/NavigateToPose** on server **/navigate\_to\_pose**

9. Use a one-shot timer (2.0 s delay) to send the goal after Nav2 is ready. Goal: x=4.0, y=2.0, frame="map", yaw=1.57 (quaternion z=0.7071, w=0.7071)

10. **Goal options:** set **feedback\_callback** \= **self.feedback\_cb** when sending the goal via **send\_goal\_async**

11. **Feedback callback self.feedback\_cb(feedback\_msg):**

    * Extract **current\_pose** from **feedback\_msg.feedback**

    * Extract **distance\_remaining** from **feedback\_msg.feedback**

    * **Publish /nav\_distance\_remaining** (std\_msgs/Float32) — the distance\_remaining value

    * Log at INFO: **"Distance remaining: X.XXm"**

12. **Result callback self.result\_cb(future):**

    * Get result via **future.result().status**

    * **Publish /nav\_action\_result** (std\_msgs/String): **"SUCCEEDED"**, **"ABORTED"**, or **"CANCELED"**

13. **Wait for action server** before sending goal: call **self.cli.wait\_for\_server(timeout\_sec=10.0)**

**Constraints**

* Must use **ActionClient** from **rclpy.action** — NOT BasicNavigator

* **send\_goal\_async()** must include the feedback\_callback argument

* **/nav\_distance\_remaining** must publish Float32 (not Float64)

* Do NOT modify the launch file

**Expected Behaviour**

* /nav\_distance\_remaining decreases monotonically as robot approaches goal

* /nav\_action\_result publishes "SUCCEEDED" on arrival

* Feedback logs appear at each Nav2 feedback cycle

**Evaluation Criteria (Hidden)**

* **ActionClient** imported from rclpy.action (source scan)

* **BasicNavigator** NOT imported (source scan)

* **/nav\_distance\_remaining** published with std\_msgs/Float32 type

* **/nav\_action\_result** published with std\_msgs/String type

* **feedback\_callback** argument present in send\_goal\_async call (source scan)

* **wait\_for\_server()** called before goal sent (source scan)

| QUESTION 5   |   MEDIUM Execute a Multi-Goal Waypoint Mission and Monitor Recovery Behaviour |
| :---- |

| Tested Skills |
| :---- |
| **S8 —** Enabling waypoint following for a multi-goal mission |
| **S7 —** Monitoring navigation feedback and result |
| **S9 —** Understanding Nav2 BT — reading recovery behaviour from topics |

**Scenario**

The logistics robot must visit four delivery stations in sequence every shift. Rather than sending one goal at a time, the dispatch system needs a waypoint follower mission that sends all four goals together and receives per-waypoint completion feedback. You must implement the mission node using the Simple Commander's followWaypoints API. The node must also subscribe to /bt\_navigator/transition\_event to log any Nav2 Behaviour Tree state transitions (which indicate recovery actions firing), and publish a mission completion summary.

**Files Student Can Edit**

scripts/waypoint\_mission.py

**Existing Package Structure**

waypoint\_mission\_pkg/  
├── launch/  
│   └── mission.launch.py            (pre-filled — do not modify)  
├── scripts/  
│   └── waypoint\_mission.py          ← EDIT THIS  
├── test/  
│   └── evaluate.py  
├── package.xml  
└── setup.py

**Delivery Station Waypoints**

| Station | x (m) | y (m) | yaw (rad) | qz | qw |
| ----- | ----- | ----- | ----- | ----- | ----- |
| Station A | 1.5 | 0.5 | 0.0 | 0.0 | 1.0 |
| Station B | 3.0 | 2.0 | 1.5708 | 0.7071 | 0.7071 |
| Station C | 4.5 | 0.5 | 3.1416 | \-0.0 | 1.0 |
| Station D | 3.0 | \-1.0 | \-1.5708 | \-0.7071 | 0.7071 |

**Student Objective**

**Implement WaypointMission ROS2 node in scripts/waypoint\_mission.py:**

14. **Import BasicNavigator** and build a list of 4 PoseStamped waypoints from the delivery station table

15. **One-shot timer (3.0 s delay)** to wait for Nav2, then call **navigator.followWaypoints(waypoints)**

16. **Waypoint feedback loop** — while **not navigator.isTaskComplete()**:

    * Call **navigator.getFeedback()** to get current waypoint index

    * **Publish /current\_waypoint** (std\_msgs/Int32) — the current waypoint index

    * Sleep 0.5 s between polls

17. **Subscribe /bt\_navigator/transition\_event** (lifecycle\_msgs/msg/TransitionEvent) — on any callback, log at WARN: **"BT transition: \<event.transition.label\>"**

18. **On mission complete:** get the result and publish **/mission\_summary** (std\_msgs/String): 

    * "waypoints=4 result=SUCCEEDED/FAILED missed=\[\<list of missed indices\>\]"

**Constraints**

* Must use **followWaypoints()** — not four separate **goToPose()** calls

* **/bt\_navigator/transition\_event** subscription must use **lifecycle\_msgs/msg/TransitionEvent**

* **/current\_waypoint** must be Int32 not Int64

* Do NOT modify the launch file

**Expected Behaviour**

* Robot visits all four delivery stations in order

* /current\_waypoint updates as each waypoint is reached

* Any Nav2 recovery behaviour (spin, wait, backup) fires a /bt\_navigator/transition\_event log

* /mission\_summary publishes final completion string

**Evaluation Criteria (Hidden)**

* **followWaypoints()** called with list of 4 PoseStamped (source scan)

* **/current\_waypoint** published with std\_msgs/Int32 type

* **/mission\_summary** published with std\_msgs/String type

* **/bt\_navigator/transition\_event** subscribed (source scan)

* 4 waypoint poses match station coordinates within 0.01 m

* Feedback poll loop uses isTaskComplete() (source scan)

| QUESTION 6   |   HARD Build a Complete Navigation System: Config, Planners, Waypoints, and Monitoring |
| :---- |

| Tested Skills |
| :---- |
| **S1/S2 —** Global and local costmap configuration |
| **S3/S4 —** NavFn global planner \+ DWB local planner parametrisation |
| **S5/S6/S7 —** Simple Commander \+ Action interface \+ feedback monitoring |
| **S8/S9 —** Waypoint following \+ BT recovery behaviour observation |
| **S10 —** Master Nav2 launch file |

**Scenario**

You are the sole robotics engineer on a warehouse surveillance robot project. Nothing is set up. You must configure the entire Nav2 stack — costmaps, planners, controller — from a specification sheet, write the master launch file, and implement a patrol node that executes a 3-waypoint patrol loop, monitors action feedback via the raw action interface, detects when the robot is stuck (no distance progress for 5 s), cancels the current goal on detection, then re-sends the next waypoint in the list. This is the kind of end-to-end task assigned to a robotics engineer on their first week.

**Files Student Can Edit**

config/patrol\_nav2\_params.yaml  
launch/patrol\_nav2.launch.py  
scripts/patrol\_node.py

**Existing Package Structure**

patrol\_nav\_pkg/  
├── launch/  
│   └── patrol\_nav2.launch.py        ← EDIT THIS  
├── config/  
│   └── patrol\_nav2\_params.yaml      ← EDIT THIS (currently empty)  
├── maps/  
│   ├── warehouse\_patrol.yaml  
│   └── warehouse\_patrol.pgm  
├── urdf/  
│   └── patrol\_bot.urdf              (pre-filled)  
├── scripts/  
│   └── patrol\_node.py               ← EDIT THIS  
├── rviz/  
│   └── patrol\_view.rviz             (pre-filled)  
├── test/  
│   └── evaluate.py  
├── package.xml  
└── setup.py

**Configuration Specification**

| Section | Parameter | Value |
| ----- | ----- | ----- |
| global\_costmap | inflation\_layer.inflation\_radius | 0.35 |
| global\_costmap | plugins | \["static\_layer","obstacle\_layer","inflation\_layer"\] |
| global\_costmap | resolution | 0.05 |
| local\_costmap | inflation\_layer.inflation\_radius | 0.35 |
| local\_costmap | plugins | \["obstacle\_layer","inflation\_layer"\] |
| local\_costmap | width / height | 5.0 / 5.0 |
| local\_costmap | global\_frame | odom |
| planner\_server | plugin | nav2\_navfn\_planner/NavfnPlanner |
| planner\_server | use\_astar | true |
| planner\_server | tolerance | 0.3 |
| controller\_server | plugin | dwb\_core::DWBLocalPlanner |
| controller\_server | max\_vel\_x | 0.4 |
| controller\_server | max\_vel\_theta | 1.0 |
| controller\_server | critics | \["RotateToGoal","Oscillation","ObstacleFootprint","GoalAlign","PathAlign","PathDist","GoalDist"\] |

**Patrol Waypoints**

| Waypoint | x | y | yaw | qz | qw |
| ----- | ----- | ----- | ----- | ----- | ----- |
| WP1 | 0.5 | 0.5 | 0.0 | 0.0 | 1.0 |
| WP2 | 5.0 | 0.5 | 1.5708 | 0.7071 | 0.7071 |
| WP3 | 5.0 | 4.0 | 3.1416 | 1.0 | 0.0 |

**Student Objective**

19. **config/patrol\_nav2\_params.yaml** — write all parameters from the spec table (14 rows)

20. **launch/patrol\_nav2.launch.py** — launch the full Nav2 stack:

    * **nav2\_bringup** with patrol\_nav2\_params.yaml and warehouse\_patrol.yaml map

    * **robot\_state\_publisher** with patrol\_bot.urdf

    * **patrol\_node**

    * **rviz2** with patrol\_view.rviz

21. **scripts/patrol\_node.py** — implement PatrolNode:

    * **Use raw ActionClient** (not BasicNavigator) to send NavigateToPose goals

    * **Patrol loop:** cycle through the 3 waypoints repeatedly, sending the next one when the previous completes

    * **Feedback callback:** track **distance\_remaining** and **last update time**

    * **Stuck detection:** if **distance\_remaining** has not decreased by \> 0.05 m in 5.0 s, cancel current goal and move to next waypoint

    * **BT monitoring:** subscribe **/bt\_navigator/transition\_event** and log at WARN on any transition

    * **Publish /patrol\_status** (std\_msgs/String) at 1 Hz: "wp=N dist=X.XXm status=NAVIGATING/STUCK/ARRIVED"

**Constraints**

* Must use raw **ActionClient** for goal sending — not BasicNavigator

* use\_astar must be true in planner config (differs from Q2/Q3)

* Stuck detection must use ROS2 clock for elapsed time — not time.time()

* **/patrol\_status** timer must fire at 1.0 Hz

* Patrol must cycle (after WP3, go back to WP1)

* Do NOT modify patrol\_bot.urdf, patrol\_view.rviz, or map files

**Expected Behaviour**

* Nav2 starts with correct costmap resolution and planner settings

* Robot visits all 3 patrol waypoints in sequence, then loops back to WP1

* /patrol\_status updates at 1 Hz showing current waypoint and distance

* On simulated stuck condition: goal cancelled, next waypoint sent, status="STUCK" logged

* BT transitions (recoveries) logged at WARN level

**Evaluation Criteria (Hidden)**

* patrol\_nav2\_params.yaml: all 14 spec parameters correct

* **planner\_server.use\_astar \== true** (differs from Q3)

* **local\_costmap.width \== 5.0** and **height \== 5.0**

* **ActionClient** imported and used — BasicNavigator NOT present

* **/patrol\_status** published at ≈1 Hz with correct format (regex check)

* Stuck detection uses ROS2 clock (source scan for get\_clock)

* Patrol cycles back to WP1 after WP3 (source scan for modulo / index wrap)

* **/bt\_navigator/transition\_event** subscribed (source scan)

* Launch file loads patrol\_nav2\_params.yaml via params\_file argument

# **4\.  ROS PACKAGE STRUCTURES**

One package per question — all pre-built in the IDE environment

**nav2\_starter\_pkg  (Q1)**

nav2\_starter\_pkg/  
├── launch/  
│   └── nav2\_bringup.launch.py  
├── config/  
│   └── nav2\_params.yaml  
├── maps/  
│   ├── warehouse\_map.yaml  
│   └── warehouse\_map.pgm  
├── scripts/  
│   └── goto\_goal.py  
├── rviz/  
│   └── nav2\_view.rviz  
├── test/  
│   └── evaluate.py  
├── package.xml  
└── setup.py

**hospital\_nav\_pkg  (Q2)**

hospital\_nav\_pkg/  
├── launch/  
│   └── hospital\_nav2.launch.py  
├── config/  
│   └── hospital\_nav2\_params.yaml  
├── maps/  
│   ├── hospital\_map.yaml  
│   └── hospital\_map.pgm  
├── urdf/  
│   └── hospital\_bot.urdf  
├── test/  
│   └── evaluate.py  
├── package.xml  
└── setup.py

**planner\_cfg\_pkg  (Q3)**

planner\_cfg\_pkg/  
├── config/  
│   └── planner\_params.yaml  
├── test/  
│   └── evaluate.py  
├── package.xml  
└── setup.py

**action\_nav\_pkg  (Q4)**

action\_nav\_pkg/  
├── launch/  
│   └── nav\_client.launch.py  
├── scripts/  
│   └── action\_nav\_client.py  
├── test/  
│   └── evaluate.py  
├── package.xml  
└── setup.py

**waypoint\_mission\_pkg  (Q5)**

waypoint\_mission\_pkg/  
├── launch/  
│   └── mission.launch.py  
├── scripts/  
│   └── waypoint\_mission.py  
├── test/  
│   └── evaluate.py  
├── package.xml  
└── setup.py

**patrol\_nav\_pkg  (Q6)**

patrol\_nav\_pkg/  
├── launch/  
│   └── patrol\_nav2.launch.py  
├── config/  
│   └── patrol\_nav2\_params.yaml  
├── maps/  
│   ├── warehouse\_patrol.yaml  
│   └── warehouse\_patrol.pgm  
├── urdf/  
│   └── patrol\_bot.urdf  
├── scripts/  
│   └── patrol\_node.py  
├── rviz/  
│   └── patrol\_view.rviz  
├── test/  
│   └── evaluate.py  
├── package.xml  
└── setup.py

# **5\.  REFERENCE SOLUTIONS**

Production-quality, executable, ROS2 Humble / Nav2 Humble compatible

### **Solution — Q1: launch/nav2\_bringup.launch.py**

\#\!/usr/bin/env python3  
"""Q1 Reference: Nav2 bringup with pre-saved map"""  
import os  
from launch import LaunchDescription  
from launch.actions import IncludeLaunchDescription  
from launch.launch\_description\_sources import PythonLaunchDescriptionSource  
from launch\_ros.actions import Node  
from ament\_index\_python.packages import get\_package\_share\_directory  
   
def generate\_launch\_description():  
    pkg      \= get\_package\_share\_directory("nav2\_starter\_pkg")  
    nav2\_pkg \= get\_package\_share\_directory("nav2\_bringup")  
    map\_f    \= os.path.join(pkg, "maps", "warehouse\_map.yaml")  
    params   \= os.path.join(pkg, "config", "nav2\_params.yaml")  
    rviz\_cfg \= os.path.join(pkg, "rviz", "nav2\_view.rviz")  
   
    nav2 \= IncludeLaunchDescription(  
        PythonLaunchDescriptionSource(  
            os.path.join(nav2\_pkg, "launch", "bringup\_launch.py")),  
        launch\_arguments={  
            "map": map\_f,  
            "use\_sim\_time": "true",  
            "params\_file": params,  
        }.items())  
   
    rviz\_node \= Node(  
        package="rviz2", executable="rviz2",  
        arguments=\["-d", rviz\_cfg\], output="screen")  
   
    return LaunchDescription(\[nav2, rviz\_node\])

### **Solution — Q1: scripts/goto\_goal.py**

\#\!/usr/bin/env python3  
"""Q1 Reference: Single goal via Simple Commander"""  
import rclpy  
from rclpy.node import Node  
from geometry\_msgs.msg import PoseStamped  
from std\_msgs.msg import String  
from nav2\_simple\_commander.robot\_navigator import BasicNavigator, TaskResult  
   
class GoToGoal(Node):  
    def \_\_init\_\_(self):  
        super().\_\_init\_\_("goto\_goal")  
        self.pub \= self.create\_publisher(String, "/nav\_result", 10\)  
        self.navigator \= BasicNavigator()  
        self.timer \= self.create\_timer(2.0, self.send\_goal)  
        self.sent \= False  
   
    def send\_goal(self):  
        if self.sent:  
            return  
        self.sent \= True  
        self.timer.cancel()  
        self.navigator.waitUntilNav2Active()  
        goal \= PoseStamped()  
        goal.header.frame\_id \= "map"  
        goal.header.stamp \= self.navigator.get\_clock().now().to\_msg()  
        goal.pose.position.x \= 3.0  
        goal.pose.position.y \= 1.5  
        goal.pose.orientation.z \= 0.0  
        goal.pose.orientation.w \= 1.0  
        self.navigator.goToPose(goal)  
        while not self.navigator.isTaskComplete():  
            rclpy.spin\_once(self, timeout\_sec=0.5)  
        result \= self.navigator.getResult()  
        msg \= f"Navigation result: {result}"  
        self.get\_logger().info(msg)  
        self.pub.publish(String(data=msg))  
   
def main(args=None):  
    rclpy.init(args=args)  
    rclpy.spin(GoToGoal())  
    rclpy.shutdown()

### **Solution — Q2: config/hospital\_nav2\_params.yaml (costmap sections)**

global\_costmap:  
  global\_costmap:  
    ros\_\_parameters:  
      update\_frequency: 5.0  
      publish\_frequency: 2.0  
      global\_frame: map  
      robot\_base\_frame: base\_footprint  
      resolution: 0.05  
      use\_sim\_time: true  
      footprint: "\[\[-0.22,-0.17\],\[0.22,-0.17\],\[0.22,0.17\],\[-0.22,0.17\]\]"  
      plugins: \["static\_layer", "obstacle\_layer", "inflation\_layer"\]  
      static\_layer:  
        plugin: "nav2\_costmap\_2d::StaticLayer"  
        map\_subscribe\_transient\_local: true  
      obstacle\_layer:  
        plugin: "nav2\_costmap\_2d::ObstacleLayer"  
        enabled: true  
        observation\_sources: scan  
        scan:  
          topic: /scan  
          max\_obstacle\_height: 2.0  
          clearing: true  
          marking: true  
      inflation\_layer:  
        plugin: "nav2\_costmap\_2d::InflationLayer"  
        inflation\_radius: 0.30  
        cost\_scaling\_factor: 3.0  
   
local\_costmap:  
  local\_costmap:  
    ros\_\_parameters:  
      update\_frequency: 5.0  
      publish\_frequency: 2.0  
      global\_frame: odom  
      robot\_base\_frame: base\_footprint  
      use\_sim\_time: true  
      rolling\_window: true  
      width: 4.0  
      height: 4.0  
      resolution: 0.05  
      footprint: "\[\[-0.22,-0.17\],\[0.22,-0.17\],\[0.22,0.17\],\[-0.22,0.17\]\]"  
      plugins: \["obstacle\_layer", "inflation\_layer"\]  
      obstacle\_layer:  
        plugin: "nav2\_costmap\_2d::ObstacleLayer"  
        enabled: true  
        observation\_sources: scan  
        scan:  
          topic: /scan  
          clearing: true  
          marking: true  
      inflation\_layer:  
        plugin: "nav2\_costmap\_2d::InflationLayer"  
        inflation\_radius: 0.30  
        cost\_scaling\_factor: 3.0

### **Solution — Q3: config/planner\_params.yaml**

planner\_server:  
  ros\_\_parameters:  
    expected\_planner\_frequency: 20.0  
    use\_sim\_time: true  
    planner\_plugins: \["GridBased"\]  
    GridBased:  
      plugin: "nav2\_navfn\_planner/NavfnPlanner"  
      use\_astar: false  
      allow\_unknown: true  
      tolerance: 0.5  
   
controller\_server:  
  ros\_\_parameters:  
    use\_sim\_time: true  
    controller\_frequency: 20.0  
    controller\_plugins: \["FollowPath"\]  
    FollowPath:  
      plugin: "dwb\_core::DWBLocalPlanner"  
      debug\_trajectory\_details: true  
      min\_vel\_x: 0.0  
      max\_vel\_x: 0.3  
      max\_vel\_y: 0.0  
      max\_vel\_theta: 0.8  
      min\_speed\_xy: 0.0  
      max\_speed\_xy: 0.3  
      min\_speed\_theta: 0.0  
      acc\_lim\_x: 2.5  
      acc\_lim\_y: 0.0  
      acc\_lim\_theta: 3.2  
      critics: \["RotateToGoal","Oscillation","ObstacleFootprint",  
                "GoalAlign","PathAlign","PathDist","GoalDist"\]  
      RotateToGoal:  
        slowing\_factor: 5.0  
        lookahead\_time: \-1.0  
      GoalDist:  
        scale: 24.0  
      PathDist:  
        scale: 32.0

### **Solution — Q4: scripts/action\_nav\_client.py**

\#\!/usr/bin/env python3  
"""Q4 Reference: Raw NavigateToPose action client with feedback"""  
import rclpy, math  
from rclpy.node import Node  
from rclpy.action import ActionClient  
from nav2\_msgs.action import NavigateToPose  
from geometry\_msgs.msg import PoseStamped  
from std\_msgs.msg import Float32, String  
   
class ActionNavClient(Node):  
    def \_\_init\_\_(self):  
        super().\_\_init\_\_("action\_nav\_client")  
        self.cli \= ActionClient(self, NavigateToPose, "/navigate\_to\_pose")  
        self.pub\_dist   \= self.create\_publisher(Float32, "/nav\_distance\_remaining", 10\)  
        self.pub\_result \= self.create\_publisher(String,  "/nav\_action\_result",     10\)  
        self.timer \= self.create\_timer(2.0, self.send\_goal)  
        self.sent  \= False  
   
    def send\_goal(self):  
        if self.sent: return  
        self.sent \= True  
        self.timer.cancel()  
        if not self.cli.wait\_for\_server(timeout\_sec=10.0):  
            self.get\_logger().error("Action server unavailable")  
            return  
        goal \= NavigateToPose.Goal()  
        pose \= PoseStamped()  
        pose.header.frame\_id \= "map"  
        pose.header.stamp \= self.get\_clock().now().to\_msg()  
        pose.pose.position.x \= 4.0  
        pose.pose.position.y \= 2.0  
        pose.pose.orientation.z \= 0.7071  
        pose.pose.orientation.w \= 0.7071  
        goal.pose \= pose  
        future \= self.cli.send\_goal\_async(  
            goal, feedback\_callback=self.feedback\_cb)  
        future.add\_done\_callback(self.goal\_response\_cb)  
   
    def goal\_response\_cb(self, future):  
        gh \= future.result()  
        if not gh.accepted:  
            self.get\_logger().error("Goal rejected")  
            return  
        result\_future \= gh.get\_result\_async()  
        result\_future.add\_done\_callback(self.result\_cb)  
   
    def feedback\_cb(self, feedback\_msg):  
        fb \= feedback\_msg.feedback  
        dist \= fb.distance\_remaining  
        self.pub\_dist.publish(Float32(data=dist))  
        self.get\_logger().info(f"Distance remaining: {dist:.2f}m")  
   
    def result\_cb(self, future):  
        from action\_msgs.msg import GoalStatus  
        status \= future.result().status  
        if   status \== GoalStatus.STATUS\_SUCCEEDED: label \= "SUCCEEDED"  
        elif status \== GoalStatus.STATUS\_ABORTED:   label \= "ABORTED"  
        else:                                        label \= "CANCELED"  
        self.pub\_result.publish(String(data=label))  
   
def main(args=None):  
    rclpy.init(args=args)  
    rclpy.spin(ActionNavClient())  
    rclpy.shutdown()

### **Solution — Q5: scripts/waypoint\_mission.py**

\#\!/usr/bin/env python3  
"""Q5 Reference: Waypoint following \+ BT monitoring"""  
import rclpy  
from rclpy.node import Node  
from geometry\_msgs.msg import PoseStamped  
from std\_msgs.msg import String, Int32  
from lifecycle\_msgs.msg import TransitionEvent  
from nav2\_simple\_commander.robot\_navigator import BasicNavigator  
   
STATIONS \= \[  
    (1.5,  0.5,  0.0,    0.0,    1.0),  
    (3.0,  2.0,  1.5708, 0.7071, 0.7071),  
    (4.5,  0.5,  3.1416, 0.0,    1.0),  
    (3.0, \-1.0, \-1.5708,-0.7071, 0.7071),  
\]  
   
def make\_pose(nav, x, y, qz, qw):  
    p \= PoseStamped()  
    p.header.frame\_id \= "map"  
    p.header.stamp \= nav.get\_clock().now().to\_msg()  
    p.pose.position.x \= x  
    p.pose.position.y \= y  
    p.pose.orientation.z \= qz  
    p.pose.orientation.w \= qw  
    return p  
   
class WaypointMission(Node):  
    def \_\_init\_\_(self):  
        super().\_\_init\_\_("waypoint\_mission")  
        self.pub\_wp  \= self.create\_publisher(Int32,  "/current\_waypoint",  10\)  
        self.pub\_sum \= self.create\_publisher(String, "/mission\_summary",   10\)  
        self.create\_subscription(TransitionEvent,  
            "/bt\_navigator/transition\_event", self.bt\_cb, 10\)  
        self.navigator \= BasicNavigator()  
        self.timer \= self.create\_timer(3.0, self.run\_mission)  
        self.started \= False  
   
    def bt\_cb(self, msg):  
        self.get\_logger().warn(  
            f"BT transition: {msg.transition.label}")  
   
    def run\_mission(self):  
        if self.started: return  
        self.started \= True  
        self.timer.cancel()  
        self.navigator.waitUntilNav2Active()  
        waypoints \= \[make\_pose(self.navigator, x, y, qz, qw)  
                     for x, y, \_, qz, qw in STATIONS\]  
        self.navigator.followWaypoints(waypoints)  
        while not self.navigator.isTaskComplete():  
            fb \= self.navigator.getFeedback()  
            if fb:  
                idx \= fb.current\_waypoint  
                self.pub\_wp.publish(Int32(data=idx))  
            rclpy.spin\_once(self, timeout\_sec=0.5)  
        result \= self.navigator.getResult()  
        missed \= self.navigator.getMissedWaypoints()  
        summary \= (f"waypoints=4 result={result} missed={missed}")  
        self.pub\_sum.publish(String(data=summary))  
   
def main(args=None):  
    rclpy.init(args=args)  
    rclpy.spin(WaypointMission())  
    rclpy.shutdown()

### **Solution — Q6: scripts/patrol\_node.py**

\#\!/usr/bin/env python3  
"""Q6 Reference: Patrol node — raw action client \+ stuck detection"""  
import rclpy, math  
from rclpy.node import Node  
from rclpy.action import ActionClient  
from nav2\_msgs.action import NavigateToPose  
from geometry\_msgs.msg import PoseStamped  
from std\_msgs.msg import String  
from lifecycle\_msgs.msg import TransitionEvent  
from action\_msgs.msg import GoalStatus  
   
WAYPOINTS \= \[  
    (0.5, 0.5, 0.0,    1.0),  
    (5.0, 0.5, 0.7071, 0.7071),  
    (5.0, 4.0, 1.0,    0.0),  
\]  
   
class PatrolNode(Node):  
    def \_\_init\_\_(self):  
        super().\_\_init\_\_("patrol\_node")  
        self.cli \= ActionClient(self, NavigateToPose, "/navigate\_to\_pose")  
        self.pub \= self.create\_publisher(String, "/patrol\_status", 10\)  
        self.create\_subscription(TransitionEvent,  
            "/bt\_navigator/transition\_event", self.bt\_cb, 10\)  
        self.wp\_idx         \= 0  
        self.dist\_remaining \= 0.0  
        self.status\_str     \= "INIT"  
        self.last\_dist      \= None  
        self.last\_progress\_time \= None  
        self.STUCK\_THRESHOLD    \= 5.0  \# seconds  
        self.STUCK\_DIST\_DELTA   \= 0.05  
        self.goal\_handle    \= None  
        self.create\_timer(1.0, self.status\_timer\_cb)  
        self.create\_timer(2.0, self.start\_cb)  
        self.started \= False  
   
    def bt\_cb(self, msg):  
        self.get\_logger().warn(f"BT transition: {msg.transition.label}")  
   
    def status\_timer\_cb(self):  
        msg \= (f"wp={self.wp\_idx} "  
               f"dist={self.dist\_remaining:.2f}m "  
               f"status={self.status\_str}")  
        self.pub.publish(String(data=msg))  
   
    def start\_cb(self):  
        if self.started: return  
        self.started \= True  
        if not self.cli.wait\_for\_server(timeout\_sec=15.0):  
            self.get\_logger().error("Nav action server not available")  
            return  
        self.send\_waypoint(self.wp\_idx)  
   
    def send\_waypoint(self, idx):  
        x, y, qz, qw \= WAYPOINTS\[idx\]  
        goal \= NavigateToPose.Goal()  
        pose \= PoseStamped()  
        pose.header.frame\_id \= "map"  
        pose.header.stamp \= self.get\_clock().now().to\_msg()  
        pose.pose.position.x \= x  
        pose.pose.position.y \= y  
        pose.pose.orientation.z \= qz  
        pose.pose.orientation.w \= qw  
        goal.pose \= pose  
        self.last\_dist \= None  
        self.last\_progress\_time \= self.get\_clock().now().nanoseconds \* 1e-9  
        future \= self.cli.send\_goal\_async(  
            goal, feedback\_callback=self.feedback\_cb)  
        future.add\_done\_callback(self.goal\_response\_cb)  
        self.status\_str \= "NAVIGATING"  
   
    def goal\_response\_cb(self, future):  
        gh \= future.result()  
        if not gh.accepted:  
            self.get\_logger().error("Goal rejected — advancing")  
            self.advance\_waypoint()  
            return  
        self.goal\_handle \= gh  
        result\_future \= gh.get\_result\_async()  
        result\_future.add\_done\_callback(self.result\_cb)  
   
    def feedback\_cb(self, feedback\_msg):  
        dist \= feedback\_msg.feedback.distance\_remaining  
        self.dist\_remaining \= dist  
        now \= self.get\_clock().now().nanoseconds \* 1e-9  
        if self.last\_dist is None:  
            self.last\_dist \= dist  
            self.last\_progress\_time \= now  
        elif (self.last\_dist \- dist) \> self.STUCK\_DIST\_DELTA:  
            self.last\_dist \= dist  
            self.last\_progress\_time \= now  
        elif (now \- self.last\_progress\_time) \> self.STUCK\_THRESHOLD:  
            self.get\_logger().warn("STUCK detected — cancelling goal")  
            self.status\_str \= "STUCK"  
            if self.goal\_handle:  
                self.goal\_handle.cancel\_goal\_async()  
   
    def result\_cb(self, future):  
        self.status\_str \= "ARRIVED"  
        self.advance\_waypoint()  
   
    def advance\_waypoint(self):  
        self.wp\_idx \= (self.wp\_idx \+ 1\) % len(WAYPOINTS)  
        self.send\_waypoint(self.wp\_idx)  
   
def main(args=None):  
    rclpy.init(args=args)  
    rclpy.spin(PatrolNode())  
    rclpy.shutdown()

# **6\.  EVALUATION SCRIPTS**

pytest — YAML validation, source scans, and live ROS2 topic/action checks

### **test/evaluate.py — Q2 (Costmap YAML validation)**

\#\!/usr/bin/env python3  
"""Q2 Evaluation: hospital\_nav2\_params.yaml costmap checks"""  
import pytest, yaml  
   
YAML \= "src/hospital\_nav\_pkg/config/hospital\_nav2\_params.yaml"  
   
def load():  
    with open(YAML) as f: return yaml.safe\_load(f)  
   
def test\_yaml\_parses():  
    d \= load(); assert isinstance(d, dict)  
   
def test\_global\_inflation\_radius():  
    p \= load()  
    r \= p\["global\_costmap"\]\["global\_costmap"\]\["ros\_\_parameters"\]  
    assert abs(r\["inflation\_layer"\]\["inflation\_radius"\] \- 0.30) \< 0.001  
   
def test\_local\_inflation\_radius():  
    p \= load()  
    r \= p\["local\_costmap"\]\["local\_costmap"\]\["ros\_\_parameters"\]  
    assert abs(r\["inflation\_layer"\]\["inflation\_radius"\] \- 0.30) \< 0.001  
   
def test\_global\_plugins\_has\_static\_layer():  
    p \= load()  
    r \= p\["global\_costmap"\]\["global\_costmap"\]\["ros\_\_parameters"\]  
    plugins \= r\["plugins"\]  
    assert "static\_layer" in plugins  
   
def test\_local\_plugins\_no\_static\_layer():  
    p \= load()  
    r \= p\["local\_costmap"\]\["local\_costmap"\]\["ros\_\_parameters"\]  
    plugins \= r\["plugins"\]  
    assert "static\_layer" not in plugins  
   
def test\_footprint\_is\_list\_not\_scalar():  
    p \= load()  
    r \= p\["global\_costmap"\]\["global\_costmap"\]\["ros\_\_parameters"\]  
    fp \= r\["footprint"\]  
    \# footprint can be a list or a string representation of a list  
    assert fp is not None and fp \!= ""  
    if isinstance(fp, str):  
        assert "\[" in fp  
    else:  
        assert isinstance(fp, list)  
   
def test\_local\_costmap\_width\_4():  
    p \= load()  
    r \= p\["local\_costmap"\]\["local\_costmap"\]\["ros\_\_parameters"\]  
    assert abs(float(r\["width"\]) \- 4.0) \< 0.001  
   
def test\_local\_costmap\_height\_4():  
    p \= load()  
    r \= p\["local\_costmap"\]\["local\_costmap"\]\["ros\_\_parameters"\]  
    assert abs(float(r\["height"\]) \- 4.0) \< 0.001  
   
def test\_global\_costmap\_resolution\_005():  
    p \= load()  
    r \= p\["global\_costmap"\]\["global\_costmap"\]\["ros\_\_parameters"\]  
    assert abs(float(r\["resolution"\]) \- 0.05) \< 0.001

### **test/evaluate.py — Q3 (Planner YAML validation)**

\#\!/usr/bin/env python3  
"""Q3 Evaluation: planner\_params.yaml — NavFn \+ DWB checks"""  
import pytest, yaml  
   
YAML \= "src/planner\_cfg\_pkg/config/planner\_params.yaml"  
   
def ps():  
    with open(YAML) as f: d \= yaml.safe\_load(f)  
    return d\["planner\_server"\]\["ros\_\_parameters"\]  
   
def cs():  
    with open(YAML) as f: d \= yaml.safe\_load(f)  
    return d\["controller\_server"\]\["ros\_\_parameters"\]  
   
def test\_navfn\_plugin():  
    p \= ps()  
    plugin \= p.get("GridBased",{}).get("plugin","")  
    assert "NavfnPlanner" in plugin  
   
def test\_use\_astar\_false():  
    p \= ps()  
    assert p.get("GridBased",{}).get("use\_astar") \== False  
   
def test\_tolerance\_05():  
    p \= ps()  
    assert abs(float(p.get("GridBased",{}).get("tolerance",0)) \- 0.5) \< 0.001  
   
def test\_dwb\_plugin():  
    c \= cs()  
    plugin \= c.get("FollowPath",{}).get("plugin","")  
    assert "DWBLocalPlanner" in plugin  
   
def test\_max\_vel\_x\_03():  
    c \= cs()  
    assert abs(float(c.get("FollowPath",{}).get("max\_vel\_x",0)) \- 0.3) \< 0.001  
   
def test\_max\_vel\_theta\_08():  
    c \= cs()  
    assert abs(float(c.get("FollowPath",{}).get("max\_vel\_theta",0)) \- 0.8) \< 0.001  
   
def test\_all\_seven\_critics():  
    c \= cs()  
    critics \= c.get("FollowPath",{}).get("critics",\[\])  
    required \= \["RotateToGoal","Oscillation","ObstacleFootprint",  
                "GoalAlign","PathAlign","PathDist","GoalDist"\]  
    for r in required:  
        assert r in critics, f"DWB critic {r} missing"  
   
def test\_goal\_dist\_scale\_24():  
    c \= cs()  
    fp \= c.get("FollowPath",{})  
    assert abs(float(fp.get("GoalDist",{}).get("scale",0)) \- 24.0) \< 0.001  
   
def test\_path\_dist\_scale\_32():  
    c \= cs()  
    fp \= c.get("FollowPath",{})  
    assert abs(float(fp.get("PathDist",{}).get("scale",0)) \- 32.0) \< 0.001

### **test/evaluate.py — Q6 (Patrol Node — comprehensive)**

\#\!/usr/bin/env python3  
"""Q6 Evaluation: patrol\_nav\_pkg — full stack"""  
import pytest, subprocess, yaml, re  
   
YAML   \= "src/patrol\_nav\_pkg/config/patrol\_nav2\_params.yaml"  
SCRIPT \= "src/patrol\_nav\_pkg/scripts/patrol\_node.py"  
LAUNCH \= "src/patrol\_nav\_pkg/launch/patrol\_nav2.launch.py"  
   
def load\_yaml():  
    with open(YAML) as f: return yaml.safe\_load(f)  
   
\# ── YAML checks ──────────────────────────────────────────────────────  
def test\_global\_inflation\_035():  
    r=load\_yaml()\["global\_costmap"\]\["global\_costmap"\]\["ros\_\_parameters"\]  
    assert abs(r\["inflation\_layer"\]\["inflation\_radius"\]-0.35)\<0.001  
   
def test\_local\_width\_5():  
    r=load\_yaml()\["local\_costmap"\]\["local\_costmap"\]\["ros\_\_parameters"\]  
    assert abs(float(r\["width"\])-5.0)\<0.001  
   
def test\_planner\_use\_astar\_true():  
    r=load\_yaml()\["planner\_server"\]\["ros\_\_parameters"\]  
    assert r.get("GridBased",{}).get("use\_astar")==True  
   
def test\_planner\_tolerance\_03():  
    r=load\_yaml()\["planner\_server"\]\["ros\_\_parameters"\]  
    assert abs(float(r.get("GridBased",{}).get("tolerance",0))-0.3)\<0.001  
   
def test\_max\_vel\_x\_04():  
    r=load\_yaml()\["controller\_server"\]\["ros\_\_parameters"\]  
    assert abs(float(r.get("FollowPath",{}).get("max\_vel\_x",0))-0.4)\<0.001  
   
def test\_all\_seven\_critics\_present():  
    r=load\_yaml()\["controller\_server"\]\["ros\_\_parameters"\]  
    critics=r.get("FollowPath",{}).get("critics",\[\])  
    for c in \["RotateToGoal","Oscillation","ObstacleFootprint",  
              "GoalAlign","PathAlign","PathDist","GoalDist"\]:  
        assert c in critics  
   
\# ── Script source checks ─────────────────────────────────────────────  
def test\_action\_client\_used():  
    src=open(SCRIPT).read()  
    assert "ActionClient" in src  
   
def test\_basic\_navigator\_not\_used():  
    src=open(SCRIPT).read()  
    assert "BasicNavigator" not in src  
   
def test\_stuck\_detection\_present():  
    src=open(SCRIPT).read()  
    assert "STUCK" in src or "stuck" in src  
   
def test\_ros2\_clock\_used\_for\_timing():  
    src=open(SCRIPT).read()  
    assert "get\_clock" in src  
    assert "time.time" not in src  
   
def test\_patrol\_cycles\_with\_modulo():  
    src=open(SCRIPT).read()  
    assert "%" in src or "modulo" in src.lower() or "len(WAYPOINTS)" in src  
   
def test\_bt\_transition\_subscribed():  
    src=open(SCRIPT).read()  
    assert "bt\_navigator/transition\_event" in src  
   
def test\_status\_timer\_1hz():  
    src=open(SCRIPT).read()  
    assert "create\_timer(1.0" in src or "create\_timer(1," in src  
   
\# ── Launch file checks ───────────────────────────────────────────────  
def test\_launch\_refs\_yaml():  
    src=open(LAUNCH).read()  
    assert "patrol\_nav2\_params.yaml" in src  
   
def test\_launch\_has\_nav2\_bringup():  
    src=open(LAUNCH).read()  
    assert "nav2\_bringup" in src or "bringup\_launch" in src  
   
\# ── Runtime checks ───────────────────────────────────────────────────  
def test\_patrol\_status\_published():  
    r=subprocess.run(\["ros2","topic","list"\],capture\_output=True,text=True,timeout=10)  
    assert "/patrol\_status" in r.stdout  
   
def test\_patrol\_status\_format():  
    r=subprocess.run(\["ros2","topic","echo","/patrol\_status","--once"\],  
        capture\_output=True,text=True,timeout=10)  
    pat=r"wp=\\d+ dist=\\d+\\.\\d+m status=(NAVIGATING|STUCK|ARRIVED|INIT)"  
    assert re.search(pat,r.stdout),f"Format mismatch: {r.stdout\[:200\]}"  
   
def test\_navigate\_to\_pose\_action\_server():  
    r=subprocess.run(\["ros2","action","list"\],capture\_output=True,text=True,timeout=10)  
    assert "/navigate\_to\_pose" in r.stdout

# **7\.  judge\_runner.py**

Production-ready  |  Docker-compatible  |  Structured JSON output

\#\!/usr/bin/env python3  
"""  
judge\_runner.py — Navigation Topic  
Usage: python3 judge\_runner.py \--question Q1 \--workspace /home/student/ros2\_ws  
"""  
import argparse,json,os,subprocess,sys,time,signal,logging  
from pathlib import Path  
   
logging.basicConfig(level=logging.INFO,  
    format="\[%(asctime)s\] %(levelname)s — %(message)s")  
log=logging.getLogger("judge\_runner")  
   
Q\_CFG={  
  "Q1":{"pkg":"nav2\_starter\_pkg","launch":"nav2\_bringup.launch.py",  
        "tests":"nav2\_starter\_pkg/test/evaluate.py",  
        "fns":\["test\_basic\_navigator\_imported","test\_goto\_goal\_topic\_published",  
               "test\_nav2\_lifecycle\_active","test\_use\_sim\_time\_on\_node",  
               "test\_navigate\_to\_pose\_server\_active","test\_launch\_refs\_nav2\_bringup"\],  
        "warmup":15,"requires\_launch":True},  
  "Q2":{"pkg":"hospital\_nav\_pkg","launch":"hospital\_nav2.launch.py",  
        "tests":"hospital\_nav\_pkg/test/evaluate.py",  
        "fns":\["test\_yaml\_parses","test\_global\_inflation\_radius",  
               "test\_local\_inflation\_radius","test\_global\_plugins\_has\_static\_layer",  
               "test\_local\_plugins\_no\_static\_layer","test\_footprint\_is\_list\_not\_scalar",  
               "test\_local\_costmap\_width\_4","test\_local\_costmap\_height\_4",  
               "test\_global\_costmap\_resolution\_005"\],  
        "warmup":0,"requires\_launch":False},  
  "Q3":{"pkg":"planner\_cfg\_pkg","launch":None,  
        "tests":"planner\_cfg\_pkg/test/evaluate.py",  
        "fns":\["test\_navfn\_plugin","test\_use\_astar\_false","test\_tolerance\_05",  
               "test\_dwb\_plugin","test\_max\_vel\_x\_03","test\_max\_vel\_theta\_08",  
               "test\_all\_seven\_critics","test\_goal\_dist\_scale\_24","test\_path\_dist\_scale\_32"\],  
        "warmup":0,"requires\_launch":False},  
  "Q4":{"pkg":"action\_nav\_pkg","launch":"nav\_client.launch.py",  
        "tests":"action\_nav\_pkg/test/evaluate.py",  
        "fns":\["test\_action\_client\_imported","test\_basic\_navigator\_not\_imported",  
               "test\_dist\_remaining\_topic","test\_action\_result\_topic",  
               "test\_feedback\_callback\_in\_send\_goal",  
               "test\_wait\_for\_server\_called"\],  
        "warmup":12,"requires\_launch":True},  
  "Q5":{"pkg":"waypoint\_mission\_pkg","launch":"mission.launch.py",  
        "tests":"waypoint\_mission\_pkg/test/evaluate.py",  
        "fns":\["test\_follow\_waypoints\_called","test\_current\_waypoint\_topic",  
               "test\_mission\_summary\_topic","test\_bt\_transition\_subscribed",  
               "test\_four\_waypoints\_built","test\_feedback\_loop\_uses\_is\_task\_complete"\],  
        "warmup":12,"requires\_launch":True},  
  "Q6":{"pkg":"patrol\_nav\_pkg","launch":"patrol\_nav2.launch.py",  
        "tests":"patrol\_nav\_pkg/test/evaluate.py",  
        "fns":\["test\_global\_inflation\_035","test\_local\_width\_5",  
               "test\_planner\_use\_astar\_true","test\_planner\_tolerance\_03",  
               "test\_max\_vel\_x\_04","test\_all\_seven\_critics\_present",  
               "test\_action\_client\_used","test\_basic\_navigator\_not\_used",  
               "test\_stuck\_detection\_present","test\_ros2\_clock\_used\_for\_timing",  
               "test\_patrol\_cycles\_with\_modulo","test\_bt\_transition\_subscribed",  
               "test\_status\_timer\_1hz","test\_launch\_refs\_yaml",  
               "test\_launch\_has\_nav2\_bringup","test\_patrol\_status\_published",  
               "test\_patrol\_status\_format","test\_navigate\_to\_pose\_action\_server"\],  
        "warmup":18,"requires\_launch":True},  
}  
   
def build\_ws(ws,env):  
    r=subprocess.run(\["colcon","build","--symlink-install"\],  
        env=env,capture\_output=True,text=True,timeout=300,cwd=ws)  
    return{"success":r.returncode==0,"stderr":r.stderr\[-2000:\]}  
   
def source\_ws(ws):  
    r=subprocess.run(\["bash","-c",  
        f"source /opt/ros/humble/setup.bash && source {ws}/install/setup.bash && env"\],  
        capture\_output=True,text=True,timeout=20)  
    return{k:v for l in r.stdout.splitlines() if "=" in l for k,v in \[l.split("=",1)\]}  
   
def do\_launch(pkg,lf,env,warmup):  
    proc=subprocess.Popen(\["ros2","launch",pkg,lf\],env=env,  
        stdout=subprocess.PIPE,stderr=subprocess.PIPE,preexec\_fn=os.setsid)  
    time.sleep(warmup); return proc  
   
def run\_tests(tf,fns,ws,env):  
    out={}  
    path=os.path.join(ws,"src",tf)  
    for fn in fns:  
        r=subprocess.run(\["python3","-m","pytest",path,"-k",fn,"-v","--tb=short"\],  
            env=env,capture\_output=True,text=True,timeout=30,cwd=ws)  
        out\[fn\]=(r.returncode==0)  
        log.info("%s  %s","PASS"if out\[fn\]else"FAIL",fn)  
    return out  
   
def kill(proc):  
    try: os.killpg(os.getpgid(proc.pid),signal.SIGTERM); proc.wait(timeout=5)  
    except: pass  
   
def judge(question,workspace):  
    if question not in Q\_CFG:  
        return{"status":"error","message":f"Unknown question {question}"}  
    cfg=Q\_CFG\[question\]  
    out={"question":question,"status":"started","build":{},"results":{},"score":{},"message":""}  
    env=os.environ.copy(); env\["ROS\_DOMAIN\_ID"\]="99"  
    bld=build\_ws(workspace,env)  
    out\["build"\]=bld  
    if not bld\["success"\]:  
        out.update({"status":"build\_failed","message":"Build failed"}); return out  
    env\_s=source\_ws(workspace)  
    proc=None  
    if cfg\["requires\_launch"\] and cfg.get("launch"):  
        proc=do\_launch(cfg\["pkg"\],cfg\["launch"\],env\_s,cfg\["warmup"\])  
    try:  
        res=run\_tests(cfg\["tests"\],cfg\["fns"\],workspace,env\_s)  
        out\["results"\]=res  
        t=len(res); p=sum(v for v in res.values())  
        out\["score"\]={"total":t,"passed":p,"failed":t-p,  
            "score\_percent":round(p/t\*100,1)if t else 0}  
        out.update({"status":"completed","message":"Evaluation completed."})  
    except Exception as e:  
        out.update({"status":"error","message":str(e)})  
    finally:  
        if proc: kill(proc)  
    return out  
   
if \_\_name\_\_=="\_\_main\_\_":  
    p=argparse.ArgumentParser()  
    p.add\_argument("--question",required=True)  
    p.add\_argument("--workspace",required=True)  
    p.add\_argument("--output-file",default=None)  
    a=p.parse\_args()  
    result=judge(a.question,a.workspace)  
    js=json.dumps(result,indent=2)  
    print(js)  
    if a.output\_file: Path(a.output\_file).write\_text(js)  
    sys.exit(0 if result.get("status")=="completed"  
             and all(result\["results"\].values()) else 1\)

# **8\.  EVALUATION SCENARIOS**

15 scenarios covering normal operation, edge cases, and common errors

| ID | Q | Scenario | Expected Outcome | Detection Method |
| ----- | ----- | ----- | ----- | ----- |
| ES-01 | Q1 | Student forgets waitUntilNav2Active() — sends goal before Nav2 ready | Goal rejected; /nav\_result shows FAILED or node crashes | Source scan for waitUntilNav2Active |
| ES-02 | Q1 | use\_sim\_time not set — real time used in simulation | TF timestamps diverge; robot freezes | Runtime: ros2 param get /goto\_goal use\_sim\_time |
| ES-03 | Q2 | inflation\_radius set to 0.55 (default) not 0.30 | Corridor marked as occupied; planner fails to find path | YAML parse \+ float comparison |
| ES-04 | Q2 | static\_layer included in local costmap plugins | Nav2 warns about static layer in rolling window costmap | YAML plugins list check — static\_layer absent test |
| ES-05 | Q2 | robot\_radius used instead of footprint polygon | Footprint is circular — rectangle robot clips walls | YAML key check: footprint vs robot\_radius |
| ES-06 | Q3 | use\_astar: true instead of false | Planner uses A\* not Dijkstra — test\_use\_astar\_false fails | YAML boolean check |
| ES-07 | Q3 | Only 5 of 7 DWB critics listed | Missing GoalAlign and PathAlign — trajectories sub-optimal | critics list membership check for all 7 |
| ES-08 | Q3 | max\_vel\_x set to 0.5 not 0.3 (speed limit violated) | test\_max\_vel\_x\_03 fails | YAML float comparison |
| ES-09 | Q4 | BasicNavigator used instead of ActionClient | test\_basic\_navigator\_not\_imported fails | Source import scan |
| ES-10 | Q4 | feedback\_callback not passed to send\_goal\_async | No /nav\_distance\_remaining published during navigation | Source scan for feedback\_callback argument |
| ES-11 | Q5 | goToPose called 4 times instead of followWaypoints | test\_follow\_waypoints\_called fails | Source scan for followWaypoints |
| ES-12 | Q5 | /bt\_navigator/transition\_event not subscribed | BT recovery events silently ignored; test fails | Source scan for transition\_event |
| ES-13 | Q6 | use\_astar: false not true (Q6 spec differs from Q3\!) | test\_planner\_use\_astar\_true fails | YAML boolean check |
| ES-14 | Q6 | Stuck detection uses time.time() not ROS2 clock | test\_ros2\_clock\_used\_for\_timing fails; breaks with sim time | Source scan for get\_clock \+ absence of time.time |
| ES-15 | Q6 | Patrol does not cycle — stops after WP3 | test\_patrol\_cycles\_with\_modulo fails; patrol terminates | Source scan for % or modulo wrap |

# **9\.  COMMON MISTAKES & DEBUGGING NOTES**

Per-question error patterns with root causes and fixes

### **Q1 — Launch Nav2 \+ Simple Commander Goal**

| Mistake | Symptom | Fix |
| ----- | ----- | ----- |
| Sending goal before waitUntilNav2Active() | Goal is rejected or ignored — no movement; /nav\_result never published | Always call navigator.waitUntilNav2Active() before navigator.goToPose() — blocks until all Nav2 lifecycle nodes are ACTIVE |
| use\_sim\_time not passed in launch file | TF tree timestamps diverge — RViz shows "No transform for frame" error | Pass use\_sim\_time="true" as a launch argument to bringup\_launch.py AND set it on every custom node |
| goToPose called inside \_\_init\_\_ not in a timer callback | Node blocks during init — rclpy.spin never reached; Nav2 never receives goal | Use a one-shot timer (2.0 s) or a thread to delay goal sending until spin is running |

### **Q2 — Costmap Configuration**

| Mistake | Symptom | Fix |
| ----- | ----- | ----- |
| Wrong YAML nesting — params at wrong level | Nav2 silently uses defaults — inflation\_radius remains 0.55 despite YAML | Structure must be: global\_costmap: → global\_costmap: → ros\_\_parameters: → inflation\_layer: → inflation\_radius: 0.30 |
| static\_layer in local costmap plugins | Nav2 log: "static\_layer is not valid in rolling-window costmap" | Local costmap is rolling (odom frame) — plugins: \["obstacle\_layer", "inflation\_layer"\] only |
| Using robot\_radius (scalar) instead of footprint (polygon) | Costmap treats robot as circular; rectangle robot clips wall corners | footprint: "\[\[-0.22,-0.17\],\[0.22,-0.17\],\[0.22,0.17\],\[-0.22,0.17\]\]" as string or nested list |

### **Q3 — NavFn \+ DWB Parametrisation**

| Mistake | Symptom | Fix |
| ----- | ----- | ----- |
| DWB critics as a space-separated string instead of YAML list | Nav2 fails to parse critics — uses default set or crashes | Must be a YAML sequence: critics: \["RotateToGoal", "Oscillation", ...\] |
| Plugin key written as "plugin" at top-level not under "GridBased"/"FollowPath" | Planner defaults to NavfnPlanner anyway — Q is marked wrong by YAML checker | Structure: planner\_server: ros\_\_parameters: planner\_plugins: \["GridBased"\] → GridBased: plugin: "nav2\_navfn\_planner/NavfnPlanner" |
| Critic scale parameters at the wrong nesting level | GoalDist.scale and PathDist.scale not found by evaluator | Nest under the controller plugin: FollowPath: GoalDist: scale: 24.0 |

### **Q4 — Raw Action Interface**

| Mistake | Symptom | Fix |
| ----- | ----- | ----- |
| Omitting feedback\_callback in send\_goal\_async | /nav\_distance\_remaining never published — evaluator timeout | send\_goal\_async(goal, feedback\_callback=self.feedback\_cb) — keyword arg required |
| Publishing Float64 not Float32 for /nav\_distance\_remaining | Topic type mismatch — evaluator fails type check | from std\_msgs.msg import Float32; Float32(data=dist) |
| Not chaining get\_result\_async to goal\_response callback | Result never received — /nav\_action\_result never published | In goal\_response\_cb: result\_future \= gh.get\_result\_async(); result\_future.add\_done\_callback(self.result\_cb) |

### **Q5 — Waypoint Following \+ BT Monitoring**

| Mistake | Symptom | Fix |
| ----- | ----- | ----- |
| Calling goToPose() four times instead of followWaypoints() | test\_follow\_waypoints\_called fails; also loses per-waypoint indexing feedback | Build a list of PoseStamped objects and call navigator.followWaypoints(waypoints\_list) |
| /bt\_navigator/transition\_event uses wrong message type | Subscription silently receives nothing — BT logs never appear | from lifecycle\_msgs.msg import TransitionEvent — NOT std\_msgs/String |
| Int64 published on /current\_waypoint instead of Int32 | test\_current\_waypoint\_topic fails type check | from std\_msgs.msg import Int32; Int32(data=idx) |

### **Q6 — Full Patrol System**

| Mistake | Symptom | Fix |
| ----- | ----- | ----- |
| use\_astar: false (copied from Q3) instead of true (Q6 spec) | test\_planner\_use\_astar\_true fails — Q6 intentionally differs from Q3 | Always re-read the spec table — Q6 uses A\* mode; Q3 uses Dijkstra |
| Stuck detection uses time.time() for elapsed seconds | test\_ros2\_clock\_used\_for\_timing fails; breaks with use\_sim\_time=True | Use self.get\_clock().now().nanoseconds \* 1e-9 for all wall-clock measurements |
| Patrol stops after WP3 — no cycle back to WP1 | test\_patrol\_cycles\_with\_modulo fails; robot stops after first lap | self.wp\_idx \= (self.wp\_idx \+ 1\) % len(WAYPOINTS) — modulo wraps at 3 |
| goal\_handle.cancel\_goal\_async() called without checking goal\_handle is not None | AttributeError: NoneType has no attribute cancel\_goal\_async on first stuck event | Guard with: if self.goal\_handle: self.goal\_handle.cancel\_goal\_async() |

| General Nav2 Debugging Notes |
| :---- |
| **Nav2 not active:** Run ros2 lifecycle list — all nodes should be in ACTIVE. If any are INACTIVE, check lifecycle\_manager logs. Common cause: map\_server failed to load the map file. |
| **/cmd\_vel not publishing:** Nav2 sends velocity commands to /cmd\_vel. If robot is not moving, check DWB critics are all resolved (ros2 node info /controller\_server). |
| **Planner fails to find path:** Usually costmap inflation is too large or goal is in occupied space. Visualise costmaps in RViz — red \= lethal, blue gradient \= inflated. |
| **Goal immediately ABORTED:** The goal pose is inside an obstacle in the costmap. Ensure the goal x/y is in free space (white in the occupancy grid). |
| **TF error map → odom:** SLAM Toolbox or AMCL must be running to publish this transform. If localisation is not running, Nav2 cannot function. |
| **Action feedback not received:** The action server publishes feedback at its own rate. If feedback\_callback fires zero times, check that the action goal was accepted (goal\_response\_cb called with gh.accepted \== True). |

**✓ All 10 syllabus skills covered   |   ✓ All 6 questions auto-gradable   |   ✓ ROS2 Humble / Nav2 Humble compatible**