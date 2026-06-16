NIAT  |  NxtWave Robotics & AI Platform  
**Coding Assessment  —  Topic Series**

**SLAM**  
**Simultaneous Localisation and Mapping**  
SLAM Toolbox  |  AMCL-style Localisation  |  Map Management  |  ROS2 Humble  
6 Auto-Graded Coding Questions  |  Easy → Hard  |  Ubuntu 22.04 / Python 3.10  
**Simulation prereqs assumed complete. No Nav2 path-planning or costmaps introduced.**

# **1\.  TOPIC ANALYSIS**

Scope, platform context, and assessment philosophy

**Topic:** SLAM — Simultaneous Localisation and Mapping

**Platform:** ROS2 Humble  |  Ubuntu 22.04  |  Python 3.10  |  SLAM Toolbox  |  Gazebo Classic  |  RViz2

SLAM is the capability that allows a robot to explore an unknown environment, build a consistent occupancy grid map from LiDAR data, and subsequently localise itself within that map on re-entry. This assessment tests whether students can configure and run SLAM Toolbox in online async mode, interpret the quality of a live map through /map and /scan topics, save and serialise a completed map to disk, reload it for AMCL-style localisation, and write ROS2 Python nodes that work with these capabilities programmatically. Every question is strictly bounded to this syllabus. No Nav2 path-planning, costmaps, behaviour trees, or motion controllers are introduced.

# **2\.  SKILLS BEING TESTED**

Syllabus coverage matrix — every skill mapped to at least one question

| ID | Skill | Covered By |
| ----- | ----- | ----- |
| S1 | Running slam\_toolbox to generate an occupancy grid map from LiDAR | Q1, Q2, Q6 |
| S2 | Configuring slam\_toolbox YAML parameters (mode, resolution, update thresholds) | Q2, Q6 |
| S3 | Saving and serialising a completed map (map\_saver\_cli \+ slam\_toolbox serialise) | Q3, Q6 |
| S4 | Loading a saved map and launching AMCL-style localisation with slam\_toolbox | Q4, Q6 |
| S5 | Interpreting /map topic (OccupancyGrid) — header, metadata, data array | Q1, Q5, Q6 |
| S6 | Interpreting /scan topic (LaserScan) — range quality, angle coverage, update rate | Q1, Q5 |
| S7 | Diagnosing mapping quality from /map and /scan topic data | Q5, Q6 |
| S8 | Writing a ROS2 launch file that starts the full SLAM stack | Q2, Q4, Q6 |
| S9 | Visualising SLAM output in RViz2 (Map, LaserScan, RobotModel, TF displays) | Q1, Q4, Q6 |
| S10 | Using map\_saver\_cli to save .pgm and .yaml map files | Q3, Q6 |

**All 10 skills covered.** No syllabus skill is untested.

# **3\.  SIX CODING QUESTIONS**

Difficulty: Easy → Hard  |  All questions are auto-gradable

| QUESTION 1   |   EASY Launch SLAM Toolbox and Verify Map Generation |
| :---- |

| Tested Skills |
| :---- |
| **S1 —** Running slam\_toolbox to generate an occupancy grid map |
| **S5 —** Interpreting the /map topic (OccupancyGrid metadata) |
| **S6 —** Interpreting the /scan topic (LaserScan range data) |
| **S9 —** Visualising SLAM output in RViz2 |

**Scenario**

You have just been assigned to the mapping team at an autonomous warehouse startup. The Gazebo environment is already running with the warehouse robot publishing /scan. Your task is to write a launch file that starts slam\_toolbox in online\_async mode, then write a short ROS2 Python subscriber node that confirms the map is being built by printing the occupancy grid dimensions and the total number of known cells each time the /map topic updates.

**Files Student Can Edit**

launch/start\_slam.launch.py  
scripts/map\_monitor.py

**Existing Package Structure**

slam\_starter\_pkg/  
├── launch/  
│   └── start\_slam.launch.py        ← EDIT THIS  
├── config/  
│   └── slam\_params.yaml            (pre-filled — do not modify)  
├── scripts/  
│   └── map\_monitor.py              ← EDIT THIS  
├── rviz/  
│   └── slam\_view.rviz              (pre-filled)  
├── test/  
│   └── evaluate.py  
├── package.xml  
└── setup.py

**Pre-filled slam\_params.yaml (read-only excerpt)**

slam\_toolbox:  
  ros\_\_parameters:  
    use\_sim\_time: true  
    slam\_mode: mapping  
    odom\_frame: odom  
    map\_frame: map  
    base\_frame: base\_footprint  
    scan\_topic: /scan  
    resolution: 0.05

**Student Objective**

1. **In launch/start\_slam.launch.py:**

   * Launch **slam\_toolbox** node (**async\_slam\_toolbox\_node**) with **use\_sim\_time=true** and the provided **slam\_params.yaml** as parameter file

   * Launch **rviz2** with the provided **rviz/slam\_view.rviz** config

2. **In scripts/map\_monitor.py — implement MapMonitor ROS2 node:**

   * **Subscribe: /map** (nav\_msgs/OccupancyGrid)

   * On each callback, compute:

     - **width \= msg.info.width**,  **height \= msg.info.height**,  **resolution \= msg.info.resolution**

     - **known\_cells** \= count of cells in msg.data where value \>= 0 (i.e. not \-1 / unknown)

     - **free\_cells** \= count of cells where value \== 0

     - **occupied\_cells** \= count of cells where value \> 0

   * Log at INFO: **"map=WxH res=R  known=K free=F occupied=O"**

   * **Publish /map\_stats** (std\_msgs/String) — the same formatted string on every /map callback

**Constraints**

* Do NOT modify slam\_params.yaml

* Use **use\_sim\_time=True** on the map\_monitor node

* Cell counting must use Python list comprehensions — no numpy

* Do NOT modify slam\_view.rviz

**Expected Behaviour**

* /map topic is being published by slam\_toolbox at approximately 1 Hz

* /map\_stats publishes a correctly formatted string on each map update

* As the robot explores, known\_cells count increases monotonically

* RViz shows the growing occupancy grid alongside the LiDAR scan overlay

**Evaluation Criteria (Hidden)**

* **slam\_toolbox** node is active and publishing /map

* /map\_stats topic is published with std\_msgs/String type

* Computed width and height match msg.info.width and msg.info.height

* known\_cells \= total cells \- count of \-1 entries (verified with injected map)

* free \+ occupied \+ unknown \= total cells

* Launch file loads slam\_params.yaml as a parameter file (not inline params)

| QUESTION 2   |   EASY-MEDIUM Configure SLAM Toolbox Parameters for a Specific Mapping Environment |
| :---- |

| Tested Skills |
| :---- |
| **S1 —** Running slam\_toolbox to generate an occupancy grid |
| **S2 —** Configuring slam\_toolbox YAML parameters |
| **S8 —** Writing a ROS2 launch file for the SLAM stack |

**Scenario**

The mapping team has been given a specification sheet from the site manager of a narrow-corridor factory floor. The environment demands a higher-resolution map (0.025 m per cell instead of the default 0.05 m), more conservative update thresholds to avoid false-positive updates when the robot vibrates, and a scan range capped at 8.0 m (the corridor is only 12 m long and longer rays bounce off glass panels unreliably). You must author the slam\_toolbox parameter YAML from scratch to match the site spec and wire it into a launch file.

**Files Student Can Edit**

config/factory\_slam.yaml  
launch/factory\_slam.launch.py

**Existing Package Structure**

factory\_slam\_pkg/  
├── launch/  
│   └── factory\_slam.launch.py     ← EDIT THIS  
├── config/  
│   └── factory\_slam.yaml          ← EDIT THIS (currently empty)  
├── urdf/  
│   └── factory\_bot.urdf           (pre-filled)  
├── worlds/  
│   └── factory\_corridor.world     (pre-filled)  
├── test/  
│   └── evaluate.py  
├── package.xml  
└── setup.py

**Site Specification (from site manager)**

| Parameter | Required Value | Reason |
| ----- | ----- | ----- |
| mode | mapping | Building new map — not localisation |
| resolution | 0.025 | High-detail narrow corridors |
| minimum\_travel\_distance | 0.3 | Reduce vibration-triggered updates |
| minimum\_travel\_heading | 0.3 | Conservative heading threshold |
| map\_update\_interval | 3.0 | Update map every 3 seconds |
| max\_laser\_range | 8.0 | Cap at 8 m — glass reflections beyond |
| use\_sim\_time | true | Running in Gazebo |
| scan\_topic | /scan | Standard LiDAR topic |
| odom\_frame | odom | Standard odometry frame |
| base\_frame | base\_footprint | Robot base frame |
| map\_frame | map | Global map frame |

**Student Objective**

3. **In config/factory\_slam.yaml** — write the complete slam\_toolbox parameter file matching ALL 11 values from the site spec table

4. **In launch/factory\_slam.launch.py** — launch the full SLAM stack:

   * **gazebo\_ros** — with factory\_corridor.world

   * **robot\_state\_publisher** — with factory\_bot.urdf

   * **spawn\_entity** — spawn robot at x=0, y=0, z=0.1

   * **async\_slam\_toolbox\_node** — using factory\_slam.yaml as parameter file

**Constraints**

* All 11 parameters must be set — evaluator checks each individually

* **params\_file** in the launch node must point to factory\_slam.yaml (not inline params)

* Do NOT modify factory\_bot.urdf or factory\_corridor.world

**Expected Behaviour**

* SLAM Toolbox starts without errors using the custom YAML

* **ros2 param get /slam\_toolbox resolution** returns 0.025

* **ros2 param get /slam\_toolbox max\_laser\_range** returns 8.0

* /map is published with resolution 0.025 m (verified via msg.info.resolution)

**Evaluation Criteria (Hidden)**

* factory\_slam.yaml is valid YAML that parses without error

* All 11 parameters match specification (parsed from YAML, not from running node)

* **/slam\_toolbox** node is active

* **/map** msg.info.resolution \== 0.025 within 1e-4

* launch file references factory\_slam.yaml via file path (source scan)

| QUESTION 3   |   EASY-MEDIUM Save a Completed Map Using map\_saver\_cli and Serialise with SLAM Toolbox |
| :---- |

| Tested Skills |
| :---- |
| **S3 —** Saving and serialising a completed map |
| **S10 —** Using map\_saver\_cli to save .pgm and .yaml map files |

**Scenario**

The robot has finished its mapping run and the team needs to persist the map. There are two artefacts required: (1) a standard .pgm \+ .yaml map pair for Nav2 and other consumers, produced by map\_saver\_cli, and (2) a SLAM Toolbox serialised .data \+ .posegraph pair that allows the mapping session to be resumed later. Your task is to write a Python ROS2 node that automates this double-save process when it receives a trigger on a /save\_map topic, and to write the corresponding launch file.

**Files Student Can Edit**

scripts/map\_saver\_node.py  
launch/save\_map.launch.py

**Existing Package Structure**

map\_save\_pkg/  
├── launch/  
│   └── save\_map.launch.py          ← EDIT THIS  
├── scripts/  
│   └── map\_saver\_node.py           ← EDIT THIS  
├── maps/  
│   └── (empty — output goes here)  
├── test/  
│   └── evaluate.py  
├── package.xml  
└── setup.py

**Student Objective**

5. **In scripts/map\_saver\_node.py — implement the MapSaverNode ROS2 node:**

   * **Declare parameters: map\_output\_dir** (default "maps/"),  **map\_name** (default "my\_map")

   * **Subscribe: /save\_map** (std\_msgs/String) — trigger message; data field is ignored

   * On trigger callback, execute two subprocess calls:

     - **Step 1 — map\_saver\_cli:** ros2 run nav2\_map\_server map\_saver\_cli \-f \<map\_output\_dir\>/\<map\_name\>

     - **Step 2 — slam\_toolbox serialise service:** call the **/slam\_toolbox/serialize\_map** service (slam\_toolbox/srv/SerializePoseGraph) with **filename \= \<map\_output\_dir\>/\<map\_name\>**

   * **Publisher: /save\_map\_status** (std\_msgs/String) — publish "SAVED: \<path\>" on success or "ERROR: \<msg\>" on failure

6. **In launch/save\_map.launch.py** — launch the map\_saver\_node with use\_sim\_time=True

**Service Call Reference**

\# slam\_toolbox/srv/SerializePoseGraph  
string filename  
\---  
\# (no response fields)  
   
\# Call via Python rclpy:  
from slam\_toolbox.srv import SerializePoseGraph  
cli \= node.create\_client(SerializePoseGraph, "/slam\_toolbox/serialize\_map")  
req \= SerializePoseGraph.Request()  
req.filename \= "/path/to/maps/my\_map"  
future \= cli.call\_async(req)

**Constraints**

* **map\_saver\_cli** must be called via subprocess — not a direct ROS2 service call

* Serialise must use the **/slam\_toolbox/serialize\_map** service via rclpy client

* Both output paths must use the map\_output\_dir and map\_name parameters

* **/save\_map\_status** must publish the result — do NOT just log it

**Expected Behaviour**

* Publishing any string to **/save\_map** triggers the save sequence

* After completion: **maps/my\_map.pgm** and **maps/my\_map.yaml** exist on disk

* After completion: **maps/my\_map.data** and **maps/my\_map.posegraph** exist on disk

* **/save\_map\_status** publishes "SAVED: maps/my\_map"

**Evaluation Criteria (Hidden)**

* **/save\_map\_status** topic is published with correct type

* Triggering /save\_map creates .pgm \+ .yaml files within 15 s

* map\_name and map\_output\_dir come from ROS2 parameters

* **/slam\_toolbox/serialize\_map** service is called (verified from rclpy client creation in source)

* ERROR branch publishes status string on subprocess failure

| QUESTION 4   |   MEDIUM Load a Saved Map and Configure SLAM Toolbox Localisation Mode |
| :---- |

| Tested Skills |
| :---- |
| **S4 —** Loading a saved map and launching AMCL-style localisation |
| **S8 —** Writing a ROS2 launch file for the full SLAM localisation stack |
| **S9 —** Visualising localisation output in RViz2 |

**Scenario**

The mapping phase is complete. The warehouse robot now needs to localise itself against the previously saved map on every subsequent deployment. SLAM Toolbox provides a localisation mode (localization) that loads a serialised pose graph and tracks the robot pose without updating the map. Your task is to write the localisation launch file that: loads the map via map\_server, starts slam\_toolbox in localization mode, and opens RViz2 configured to show the static map with the robot's estimated position.

**Files Student Can Edit**

launch/localise.launch.py  
config/localise\_params.yaml  
rviz/localise\_view.rviz

**Existing Package Structure**

localisation\_pkg/  
├── launch/  
│   └── localise.launch.py          ← EDIT THIS  
├── config/  
│   └── localise\_params.yaml        ← EDIT THIS (currently empty)  
├── maps/  
│   ├── warehouse\_map.yaml          (pre-saved — do not modify)  
│   ├── warehouse\_map.pgm           (pre-saved — do not modify)  
│   ├── warehouse\_map.data          (pre-saved — do not modify)  
│   └── warehouse\_map.posegraph     (pre-saved — do not modify)  
├── rviz/  
│   └── localise\_view.rviz          ← EDIT THIS  
├── urdf/  
│   └── warehouse\_bot.urdf          (pre-filled)  
├── test/  
│   └── evaluate.py  
├── package.xml  
└── setup.py

**Student Objective**

7. **In config/localise\_params.yaml** — write the slam\_toolbox parameter file for localisation mode:

   * **mode: localization** (NOT mapping)

   * **map\_file\_name**: absolute or package-relative path to maps/warehouse\_map (no extension)

   * **map\_start\_at\_dock: true**

   * Standard frames: odom, map, base\_footprint; scan\_topic: /scan; use\_sim\_time: true

8. **In launch/localise.launch.py** — launch five nodes:

   * **map\_server** (nav2\_map\_server) — load maps/warehouse\_map.yaml, use\_sim\_time=True

   * **lifecycle\_manager** — manage map\_server lifecycle (node\_names: \["map\_server"\])

   * **robot\_state\_publisher** — with warehouse\_bot.urdf

   * **slam\_toolbox** (localization\_slam\_toolbox\_node) — with localise\_params.yaml

   * **rviz2** — with localise\_view.rviz

9. **In rviz/localise\_view.rviz** — configure three displays:

   * **Map** — topic: /map, alpha: 0.7, fixed frame: map

   * **RobotModel** — /robot\_description

   * **LaserScan** — /scan, size: 0.03 m

**Constraints**

* **mode** must be **localization** — if set to mapping, the evaluator fails the mode check

* **lifecycle\_manager** is required — map\_server will not publish /map without it

* Do NOT use AMCL — localisation must be via slam\_toolbox localization mode

* Do NOT modify the pre-saved map files

**Expected Behaviour**

* /map topic publishes the pre-saved warehouse map (static, not growing)

* **/slam\_toolbox** node is active in localisation mode (not generating new map cells)

* RViz shows the static map with the robot model overlaid

* As the robot moves, its pose updates against the fixed map

**Evaluation Criteria (Hidden)**

* localise\_params.yaml has mode: localization (not mapping)

* map\_server node is active and publishing /map

* **localization\_slam\_toolbox\_node** is the executable (not async\_slam\_toolbox\_node)

* lifecycle\_manager is present in launch file (source scan)

* /map msg.info matches pre-saved map dimensions

* localise\_view.rviz contains Map, RobotModel, and LaserScan displays

| QUESTION 5   |   MEDIUM Build a Map Quality Diagnostics Node Using /map and /scan |
| :---- |

| Tested Skills |
| :---- |
| **S5 —** Interpreting /map topic (OccupancyGrid) data array |
| **S6 —** Interpreting /scan topic (LaserScan) range quality |
| **S7 —** Diagnosing mapping quality from /map and /scan |

**Scenario**

The quality assurance team needs a diagnostic node that continuously monitors both the occupancy map and the incoming LiDAR scans to produce a mapping quality score. Poor map quality indicators include: a high proportion of unknown cells in the map, a low proportion of valid (finite, in-range) scan readings, and inconsistency between the scan coverage angle and the expected 360°. Your task is to implement this diagnostics node and publish a structured quality report at 0.5 Hz.

**Files Student Can Edit**

scripts/map\_diagnostics.py

**Existing Package Structure**

map\_diagnostics\_pkg/  
├── launch/  
│   └── diagnostics.launch.py      (pre-filled — do not modify)  
├── scripts/  
│   └── map\_diagnostics.py         ← EDIT THIS  
├── test/  
│   └── evaluate.py  
├── package.xml  
└── setup.py

**Student Objective**

**Implement the MapDiagnostics ROS2 node in scripts/map\_diagnostics.py:**

10. **Subscription A: /map** (nav\_msgs/OccupancyGrid)

    * Store latest map. Compute:

      - **unknown\_ratio \= count(-1 cells) / total\_cells**

      - **occupied\_ratio \= count(cells \> 0\) / total\_cells**

11. **Subscription B: /scan** (sensor\_msgs/LaserScan)

    * Store latest scan. Compute:

      - **valid\_ratio** \= count of finite ranges within \[range\_min, range\_max\] / total ranges

      - **angular\_coverage\_deg** \= (angle\_max \- angle\_min) \* 180 / pi   (full 360 \= 360.0)

12. **Timer at 0.5 Hz (period=2.0 s) — compute and publish quality report:**

    * **map\_quality:** "GOOD" if unknown\_ratio \< 0.4, else "POOR"

    * **scan\_quality:** "GOOD" if valid\_ratio \> 0.8 and angular\_coverage\_deg \>= 350.0, else "POOR"

    * **overall:** "OK" if both GOOD, else "DEGRADED"

13. **Publisher: /map\_quality\_report** (std\_msgs/String) — publish structured string:

"map=GOOD/POOR unknown=X.XX occupied=X.XX  scan=GOOD/POOR valid=X.XX coverage=XXX.Xdeg  overall=OK/DEGRADED"

14. **Parameters (declare and read):**

    * **unknown\_threshold** (default 0.4) — map quality boundary

    * **valid\_scan\_threshold** (default 0.8) — scan quality boundary

**Constraints**

* Do NOT use numpy — use Python list comprehensions and math module only

* **angular\_coverage\_deg** must use math.pi for the conversion

* Timer must fire at 0.5 Hz (period \= 2.0 s)

* If no /map received yet, use unknown\_ratio=1.0; if no /scan yet, use valid\_ratio=0.0

**Expected Behaviour**

* /map\_quality\_report published at 0.5 Hz

* A fully explored map (few unknowns) produces map\_quality="GOOD"

* A degraded LiDAR (many inf readings) produces scan\_quality="POOR"

* overall="DEGRADED" when either sensor quality is POOR

**Evaluation Criteria (Hidden)**

* /map\_quality\_report published with std\_msgs/String type

* Injected map with 20% unknown cells → map\_quality="GOOD" (below 0.4 threshold)

* Injected map with 60% unknown cells → map\_quality="POOR"

* Injected scan with 90% valid ranges \+ 360° → scan\_quality="GOOD"

* Injected scan with 50% inf ranges → scan\_quality="POOR"

* unknown\_threshold and valid\_scan\_threshold parameters declared and honoured

* Timer at 2.0 s (source scan for create\_timer(2.0))

| QUESTION 6   |   HARD Build a Complete SLAM Pipeline: Map, Save, Localise, and Diagnose |
| :---- |

| Tested Skills |
| :---- |
| **S1/S2 —** Run slam\_toolbox with custom config to generate a map |
| **S3/S10 —** Save and serialise the completed map |
| **S4 —** Load the saved map and switch slam\_toolbox to localisation mode |
| **S5/S6/S7 —** Subscribe to /map and /scan, compute quality metrics |
| **S8/S9 —** Single master launch file for full stack \+ RViz2 |

**Scenario**

You are the sole robotics software engineer on a hospital corridor scanning project. A Gazebo environment simulating a hospital corridor is already running, publishing /scan and /odom. Nothing else is set up. You must build the complete SLAM pipeline from scratch: a custom slam\_toolbox YAML for the narrow-corridor environment, a master launch file that brings up the full mapping stack, a node that monitors both /map and /scan and automatically triggers a map save when mapping quality becomes stable (unknown\_ratio drops below a configurable threshold for 10 consecutive seconds), and a RViz2 config showing all relevant data streams. This is a realistic end-to-end SLAM engineering ticket.

**Files Student Can Edit**

config/hospital\_slam.yaml  
launch/hospital\_slam.launch.py  
scripts/auto\_map\_saver.py  
rviz/hospital\_view.rviz

**Existing Package Structure**

hospital\_slam\_pkg/  
├── launch/  
│   └── hospital\_slam.launch.py     ← EDIT THIS (currently empty)  
├── config/  
│   └── hospital\_slam.yaml          ← EDIT THIS (currently empty)  
├── scripts/  
│   └── auto\_map\_saver.py           ← EDIT THIS (currently empty)  
├── rviz/  
│   └── hospital\_view.rviz          ← EDIT THIS (currently empty)  
├── maps/  
│   └── (output directory)  
├── test/  
│   └── evaluate.py  
├── package.xml  
└── setup.py

**Hospital Corridor Specification**

| Parameter | Value | Notes |
| ----- | ----- | ----- |
| resolution | 0.03 | 3 cm — fine enough for corridor walls |
| max\_laser\_range | 10.0 | Corridor max length is 15 m |
| minimum\_travel\_distance | 0.2 | Update every 20 cm of travel |
| minimum\_travel\_heading | 0.15 | Update every 0.15 rad of rotation |
| map\_update\_interval | 2.0 | Every 2 seconds |
| use\_sim\_time | true | Running in Gazebo |
| scan\_topic | /scan | Standard |
| odom\_frame | odom | Standard |
| base\_frame | base\_footprint | Standard |
| map\_frame | map | Standard |

**Student Objective**

15. **config/hospital\_slam.yaml** — write all 10 parameters from the specification table (mode: mapping)

16. **launch/hospital\_slam.launch.py** — launch the full mapping stack:

    * **robot\_state\_publisher** (assume hospital\_bot.urdf exists; load dynamically)

    * **async\_slam\_toolbox\_node** with hospital\_slam.yaml

    * **auto\_map\_saver** node

    * **rviz2** with hospital\_view.rviz

17. **scripts/auto\_map\_saver.py** — implement AutoMapSaver ROS2 node:

    * **Parameters: map\_output\_dir** (default "maps/"),  **map\_name** (default "hospital\_map"),  **stability\_threshold** (default 0.25),  **stability\_duration** (default 10.0 s)

    * **Subscribe /map** — on each callback compute unknown\_ratio; if unknown\_ratio \< stability\_threshold, start/continue a stability timer; if ratio rises above threshold, reset the timer

    * **Subscribe /scan** — on each callback compute valid\_ratio (finite in-range reads / total reads)

    * **Timer at 1 Hz** — check if the stability condition has been met for stability\_duration continuous seconds

    * **On stability trigger (fires once only):**

      - Run **map\_saver\_cli** subprocess to save .pgm \+ .yaml

      - Call **/slam\_toolbox/serialize\_map** service to save .data \+ .posegraph

      - **Publish /auto\_save\_status** (std\_msgs/String): "MONITORING", "STABLE", or "SAVED: \<path\>"

      - Log at INFO: **"Auto-save triggered: unknown\_ratio=X.XX"**

18. **rviz/hospital\_view.rviz** — configure four displays: Map (/map), LaserScan (/scan), RobotModel, TF

**Constraints**

* hospital\_slam.yaml must have ALL 10 parameters from the spec table

* Auto-save must fire exactly once — add a self.saved \= False guard flag

* **/slam\_toolbox/serialize\_map** must be called via rclpy service client

* Stability check must use elapsed wall-clock seconds (track first\_stable\_time with ROS2 clock)

* Do NOT use numpy — all computations use Python built-ins and math

* Do NOT modify any pre-existing files

**Expected Behaviour**

* SLAM Toolbox starts and begins generating /map at 0.03 m resolution

* /auto\_save\_status publishes "MONITORING" continuously until stability achieved

* After 10 s of unknown\_ratio \< 0.25: status changes to "STABLE" then "SAVED: maps/hospital\_map"

* maps/hospital\_map.pgm, .yaml, .data, .posegraph all exist after save

* Save fires exactly once even if robot continues moving

**Evaluation Criteria (Hidden)**

* hospital\_slam.yaml parses without error, all 10 params correct

* **/auto\_save\_status** publishes std\_msgs/String

* Status sequence: "MONITORING" → "STABLE" → "SAVED: ..."

* self.saved guard prevents double-save (verified via source scan \+ runtime test)

* stability\_threshold and stability\_duration come from ROS2 parameters

* map\_saver\_cli called via subprocess (source scan)

* **/slam\_toolbox/serialize\_map** service client created (source scan)

* .pgm and .yaml files exist on disk after save trigger

* hospital\_view.rviz contains Map, LaserScan, RobotModel, TF displays

* Launch file references hospital\_slam.yaml via file path

# **4\.  ROS PACKAGE STRUCTURES**

One package per question — all pre-built in the IDE environment

**slam\_starter\_pkg  (Q1)**

slam\_starter\_pkg/  
├── launch/  
│   └── start\_slam.launch.py  
├── config/  
│   └── slam\_params.yaml  
├── scripts/  
│   └── map\_monitor.py  
├── rviz/  
│   └── slam\_view.rviz  
├── test/  
│   └── evaluate.py  
├── package.xml  
└── setup.py

**factory\_slam\_pkg  (Q2)**

factory\_slam\_pkg/  
├── launch/  
│   └── factory\_slam.launch.py  
├── config/  
│   └── factory\_slam.yaml  
├── urdf/  
│   └── factory\_bot.urdf  
├── worlds/  
│   └── factory\_corridor.world  
├── test/  
│   └── evaluate.py  
├── package.xml  
└── setup.py

**map\_save\_pkg  (Q3)**

map\_save\_pkg/  
├── launch/  
│   └── save\_map.launch.py  
├── scripts/  
│   └── map\_saver\_node.py  
├── maps/  
│   └── (output directory)  
├── test/  
│   └── evaluate.py  
├── package.xml  
└── setup.py

**localisation\_pkg  (Q4)**

localisation\_pkg/  
├── launch/  
│   └── localise.launch.py  
├── config/  
│   └── localise\_params.yaml  
├── maps/  
│   ├── warehouse\_map.yaml  
│   ├── warehouse\_map.pgm  
│   ├── warehouse\_map.data  
│   └── warehouse\_map.posegraph  
├── rviz/  
│   └── localise\_view.rviz  
├── urdf/  
│   └── warehouse\_bot.urdf  
├── test/  
│   └── evaluate.py  
├── package.xml  
└── setup.py

**map\_diagnostics\_pkg  (Q5)**

map\_diagnostics\_pkg/  
├── launch/  
│   └── diagnostics.launch.py  
├── scripts/  
│   └── map\_diagnostics.py  
├── test/  
│   └── evaluate.py  
├── package.xml  
└── setup.py

**hospital\_slam\_pkg  (Q6)**

hospital\_slam\_pkg/  
├── launch/  
│   └── hospital\_slam.launch.py  
├── config/  
│   └── hospital\_slam.yaml  
├── scripts/  
│   └── auto\_map\_saver.py  
├── rviz/  
│   └── hospital\_view.rviz  
├── maps/  
│   └── (output directory)  
├── test/  
│   └── evaluate.py  
├── package.xml  
└── setup.py

# **5\.  REFERENCE SOLUTIONS**

Production-quality, executable, ROS2 Humble compatible — no pseudocode

### **Solution — Q1: launch/start\_slam.launch.py**

\#\!/usr/bin/env python3  
"""Q1 Reference: Start SLAM Toolbox \+ RViz2"""  
import os  
from launch import LaunchDescription  
from launch\_ros.actions import Node  
from ament\_index\_python.packages import get\_package\_share\_directory  
   
def generate\_launch\_description():  
    pkg   \= get\_package\_share\_directory("slam\_starter\_pkg")  
    cfg   \= os.path.join(pkg, "config", "slam\_params.yaml")  
    rviz  \= os.path.join(pkg, "rviz", "slam\_view.rviz")  
   
    slam\_node \= Node(  
        package="slam\_toolbox",  
        executable="async\_slam\_toolbox\_node",  
        name="slam\_toolbox",  
        output="screen",  
        parameters=\[cfg, {"use\_sim\_time": True}\])  
   
    rviz\_node \= Node(  
        package="rviz2",  
        executable="rviz2",  
        name="rviz2",  
        arguments=\["-d", rviz\],  
        output="screen")  
   
    return LaunchDescription(\[slam\_node, rviz\_node\])

### **Solution — Q1: scripts/map\_monitor.py**

\#\!/usr/bin/env python3  
"""Q1 Reference: OccupancyGrid map monitor"""  
import rclpy  
from rclpy.node import Node  
from nav\_msgs.msg import OccupancyGrid  
from std\_msgs.msg import String  
   
class MapMonitor(Node):  
    def \_\_init\_\_(self):  
        super().\_\_init\_\_("map\_monitor")  
        self.sub \= self.create\_subscription(  
            OccupancyGrid, "/map", self.map\_cb, 10\)  
        self.pub \= self.create\_publisher(String, "/map\_stats", 10\)  
   
    def map\_cb(self, msg: OccupancyGrid):  
        w    \= msg.info.width  
        h    \= msg.info.height  
        res  \= msg.info.resolution  
        data \= list(msg.data)  
        total   \= len(data)  
        unknown \= sum(1 for c in data if c \== \-1)  
        free    \= sum(1 for c in data if c \== 0\)  
        occ     \= sum(1 for c in data if c \> 0\)  
        known   \= total \- unknown  
        s \= (f"map={w}x{h} res={res:.3f}  "  
             f"known={known} free={free} occupied={occ}")  
        self.get\_logger().info(s)  
        self.pub.publish(String(data=s))  
   
def main(args=None):  
    rclpy.init(args=args)  
    rclpy.spin(MapMonitor())  
    rclpy.shutdown()  
   
if \_\_name\_\_ \== "\_\_main\_\_":  
    main()

### **Solution — Q2: config/factory\_slam.yaml**

slam\_toolbox:  
  ros\_\_parameters:  
    mode: mapping  
    resolution: 0.025  
    minimum\_travel\_distance: 0.3  
    minimum\_travel\_heading: 0.3  
    map\_update\_interval: 3.0  
    max\_laser\_range: 8.0  
    use\_sim\_time: true  
    scan\_topic: /scan  
    odom\_frame: odom  
    base\_frame: base\_footprint  
    map\_frame: map

### **Solution — Q2: launch/factory\_slam.launch.py**

\#\!/usr/bin/env python3  
"""Q2 Reference: Factory SLAM full stack"""  
import os  
from launch import LaunchDescription  
from launch.actions import IncludeLaunchDescription  
from launch.launch\_description\_sources import PythonLaunchDescriptionSource  
from launch\_ros.actions import Node  
from ament\_index\_python.packages import get\_package\_share\_directory  
   
def generate\_launch\_description():  
    pkg    \= get\_package\_share\_directory("factory\_slam\_pkg")  
    gz\_pkg \= get\_package\_share\_directory("gazebo\_ros")  
    world  \= os.path.join(pkg, "worlds", "factory\_corridor.world")  
    urdf   \= os.path.join(pkg, "urdf", "factory\_bot.urdf")  
    cfg    \= os.path.join(pkg, "config", "factory\_slam.yaml")  
   
    with open(urdf) as f:  
        robot\_desc \= f.read()  
   
    gazebo \= IncludeLaunchDescription(  
        PythonLaunchDescriptionSource(  
            os.path.join(gz\_pkg, "launch", "gazebo.launch.py")),  
        launch\_arguments={"world": world}.items())  
   
    rsp \= Node(package="robot\_state\_publisher",  
               executable="robot\_state\_publisher",  
               parameters=\[{"robot\_description": robot\_desc, "use\_sim\_time": True}\])  
   
    spawn \= Node(package="gazebo\_ros", executable="spawn\_entity.py",  
                 arguments=\["-topic","/robot\_description","-entity","factory\_bot",  
                             "-x","0","-y","0","-z","0.1"\])  
   
    slam \= Node(package="slam\_toolbox",  
                executable="async\_slam\_toolbox\_node",  
                name="slam\_toolbox",  
                parameters=\[cfg, {"use\_sim\_time": True}\],  
                output="screen")  
   
    return LaunchDescription(\[gazebo, rsp, spawn, slam\])

### **Solution — Q3: scripts/map\_saver\_node.py**

\#\!/usr/bin/env python3  
"""Q3 Reference: Automated map saver node"""  
import rclpy, subprocess, os  
from rclpy.node import Node  
from std\_msgs.msg import String  
from slam\_toolbox.srv import SerializePoseGraph  
   
class MapSaverNode(Node):  
    def \_\_init\_\_(self):  
        super().\_\_init\_\_("map\_saver\_node")  
        self.declare\_parameter("map\_output\_dir", "maps/")  
        self.declare\_parameter("map\_name", "my\_map")  
        self.out\_dir  \= self.get\_parameter("map\_output\_dir").value  
        self.map\_name \= self.get\_parameter("map\_name").value  
        self.sub \= self.create\_subscription(  
            String, "/save\_map", self.save\_cb, 10\)  
        self.pub \= self.create\_publisher(String, "/save\_map\_status", 10\)  
        self.cli \= self.create\_client(SerializePoseGraph,  
                                       "/slam\_toolbox/serialize\_map")  
   
    def save\_cb(self, msg: String):  
        full\_path \= os.path.join(self.out\_dir, self.map\_name)  
        os.makedirs(self.out\_dir, exist\_ok=True)  
        try:  
            \# Step 1: save .pgm \+ .yaml  
            subprocess.run(  
                \["ros2","run","nav2\_map\_server","map\_saver\_cli","-f",full\_path\],  
                check=True, timeout=15)  
            \# Step 2: serialise pose graph  
            req \= SerializePoseGraph.Request()  
            req.filename \= full\_path  
            self.cli.call\_async(req)  
            status \= f"SAVED: {full\_path}"  
            self.get\_logger().info(status)  
        except Exception as e:  
            status \= f"ERROR: {e}"  
            self.get\_logger().error(status)  
        self.pub.publish(String(data=status))  
   
def main(args=None):  
    rclpy.init(args=args)  
    rclpy.spin(MapSaverNode())  
    rclpy.shutdown()

### **Solution — Q4: config/localise\_params.yaml**

slam\_toolbox:  
  ros\_\_parameters:  
    mode: localization  
    map\_file\_name: maps/warehouse\_map  
    map\_start\_at\_dock: true  
    use\_sim\_time: true  
    odom\_frame: odom  
    map\_frame: map  
    base\_frame: base\_footprint  
    scan\_topic: /scan  
    resolution: 0.05

### **Solution — Q4: launch/localise.launch.py**

\#\!/usr/bin/env python3  
"""Q4 Reference: Localisation stack with map\_server \+ slam\_toolbox"""  
import os  
from launch import LaunchDescription  
from launch\_ros.actions import Node, LifecycleNode  
from nav2\_common.launch import RewrittenYaml  
from ament\_index\_python.packages import get\_package\_share\_directory  
   
def generate\_launch\_description():  
    pkg   \= get\_package\_share\_directory("localisation\_pkg")  
    urdf  \= os.path.join(pkg, "urdf", "warehouse\_bot.urdf")  
    map\_f \= os.path.join(pkg, "maps", "warehouse\_map.yaml")  
    cfg   \= os.path.join(pkg, "config", "localise\_params.yaml")  
    rviz  \= os.path.join(pkg, "rviz", "localise\_view.rviz")  
   
    with open(urdf) as f:  
        robot\_desc \= f.read()  
   
    map\_server \= LifecycleNode(  
        package="nav2\_map\_server", executable="map\_server",  
        name="map\_server", output="screen",  
        parameters=\[{"yaml\_filename": map\_f, "use\_sim\_time": True}\])  
   
    lm \= Node(package="nav2\_lifecycle\_manager",  
              executable="lifecycle\_manager",  
              name="lifecycle\_manager\_map",  
              parameters=\[{"use\_sim\_time": True,  
                           "autostart": True,  
                           "node\_names": \["map\_server"\]}\])  
   
    rsp \= Node(package="robot\_state\_publisher",  
               executable="robot\_state\_publisher",  
               parameters=\[{"robot\_description": robot\_desc,"use\_sim\_time":True}\])  
   
    slam \= Node(package="slam\_toolbox",  
                executable="localization\_slam\_toolbox\_node",  
                name="slam\_toolbox", output="screen",  
                parameters=\[cfg, {"use\_sim\_time": True}\])  
   
    rviz\_node \= Node(package="rviz2", executable="rviz2",  
                     arguments=\["-d", rviz\], output="screen")  
   
    return LaunchDescription(\[map\_server, lm, rsp, slam, rviz\_node\])

### **Solution — Q5: scripts/map\_diagnostics.py**

\#\!/usr/bin/env python3  
"""Q5 Reference: Map quality diagnostics node"""  
import rclpy, math  
from rclpy.node import Node  
from nav\_msgs.msg import OccupancyGrid  
from sensor\_msgs.msg import LaserScan  
from std\_msgs.msg import String  
   
class MapDiagnostics(Node):  
    def \_\_init\_\_(self):  
        super().\_\_init\_\_("map\_diagnostics")  
        self.declare\_parameter("unknown\_threshold",   0.4)  
        self.declare\_parameter("valid\_scan\_threshold",0.8)  
        self.unk\_thresh  \= self.get\_parameter("unknown\_threshold").value  
        self.scan\_thresh \= self.get\_parameter("valid\_scan\_threshold").value  
        self.unknown\_ratio       \= 1.0  
        self.occupied\_ratio      \= 0.0  
        self.valid\_ratio         \= 0.0  
        self.angular\_coverage    \= 0.0  
        self.create\_subscription(OccupancyGrid,"/map", self.map\_cb, 10\)  
        self.create\_subscription(LaserScan,    "/scan",self.scan\_cb,10)  
        self.pub   \= self.create\_publisher(String, "/map\_quality\_report", 10\)  
        self.timer \= self.create\_timer(2.0, self.timer\_cb)  
   
    def map\_cb(self, msg: OccupancyGrid):  
        data  \= list(msg.data)  
        total \= len(data) or 1  
        self.unknown\_ratio  \= sum(1 for c in data if c \== \-1) / total  
        self.occupied\_ratio \= sum(1 for c in data if c \> 0\)   / total  
   
    def scan\_cb(self, msg: LaserScan):  
        ranges \= list(msg.ranges)  
        total  \= len(ranges) or 1  
        valid  \= sum(1 for r in ranges  
                     if r \== r and r \!= float("inf")  
                     and msg.range\_min \<= r \<= msg.range\_max)  
        self.valid\_ratio      \= valid / total  
        self.angular\_coverage \= (msg.angle\_max \- msg.angle\_min) \* 180.0 / math.pi  
   
    def timer\_cb(self):  
        mq \= "GOOD" if self.unknown\_ratio  \< self.unk\_thresh  else "POOR"  
        sq \= "GOOD" if (self.valid\_ratio \> self.scan\_thresh  
                        and self.angular\_coverage \>= 350.0)   else "POOR"  
        ov \= "OK" if mq \== "GOOD" and sq \== "GOOD" else "DEGRADED"  
        report \= (f"map={mq} unknown={self.unknown\_ratio:.2f} occupied={self.occupied\_ratio:.2f}  "  
                  f"scan={sq} valid={self.valid\_ratio:.2f} coverage={self.angular\_coverage:.1f}deg  "  
                  f"overall={ov}")  
        self.pub.publish(String(data=report))  
   
def main(args=None):  
    rclpy.init(args=args)  
    rclpy.spin(MapDiagnostics())  
    rclpy.shutdown()

### **Solution — Q6: scripts/auto\_map\_saver.py**

\#\!/usr/bin/env python3  
"""Q6 Reference: Auto map saver with stability detection"""  
import rclpy, math, subprocess, os  
from rclpy.node import Node  
from nav\_msgs.msg import OccupancyGrid  
from sensor\_msgs.msg import LaserScan  
from std\_msgs.msg import String  
from slam\_toolbox.srv import SerializePoseGraph  
   
class AutoMapSaver(Node):  
    def \_\_init\_\_(self):  
        super().\_\_init\_\_("auto\_map\_saver")  
        for p, v in \[("map\_output\_dir","maps/"),("map\_name","hospital\_map"),  
                     ("stability\_threshold",0.25),("stability\_duration",10.0)\]:  
            self.declare\_parameter(p, v)  
        g \= self.get\_parameter  
        self.out\_dir     \= g("map\_output\_dir").value  
        self.map\_name    \= g("map\_name").value  
        self.stab\_thresh \= g("stability\_threshold").value  
        self.stab\_dur    \= g("stability\_duration").value  
        self.saved            \= False  
        self.stable\_since     \= None  
        self.unknown\_ratio    \= 1.0  
        self.valid\_ratio      \= 0.0  
        self.create\_subscription(OccupancyGrid, "/map", self.map\_cb,  10\)  
        self.create\_subscription(LaserScan,     "/scan",self.scan\_cb, 10\)  
        self.pub  \= self.create\_publisher(String, "/auto\_save\_status", 10\)  
        self.cli  \= self.create\_client(SerializePoseGraph,  
                                        "/slam\_toolbox/serialize\_map")  
        self.create\_timer(1.0, self.timer\_cb)  
   
    def map\_cb(self, msg: OccupancyGrid):  
        data  \= list(msg.data)  
        total \= len(data) or 1  
        self.unknown\_ratio \= sum(1 for c in data if c \== \-1) / total  
        now \= self.get\_clock().now().nanoseconds \* 1e-9  
        if self.unknown\_ratio \< self.stab\_thresh:  
            if self.stable\_since is None:  
                self.stable\_since \= now  
        else:  
            self.stable\_since \= None  \# reset on degradation  
   
    def scan\_cb(self, msg: LaserScan):  
        ranges \= list(msg.ranges)  
        total  \= len(ranges) or 1  
        valid  \= sum(1 for r in ranges  
                     if r \== r and r \!= float("inf")  
                     and msg.range\_min \<= r \<= msg.range\_max)  
        self.valid\_ratio \= valid / total  
   
    def timer\_cb(self):  
        if self.saved:  
            return  
        now \= self.get\_clock().now().nanoseconds \* 1e-9  
        if self.stable\_since is not None:  
            elapsed \= now \- self.stable\_since  
            if elapsed \>= self.stab\_dur:  
                self.pub.publish(String(data="STABLE"))  
                self.\_do\_save()  
                return  
        self.pub.publish(String(data="MONITORING"))  
   
    def \_do\_save(self):  
        full \= os.path.join(self.out\_dir, self.map\_name)  
        os.makedirs(self.out\_dir, exist\_ok=True)  
        try:  
            subprocess.run(  
                \["ros2","run","nav2\_map\_server","map\_saver\_cli","-f",full\],  
                check=True, timeout=20)  
            req \= SerializePoseGraph.Request()  
            req.filename \= full  
            self.cli.call\_async(req)  
            self.saved \= True  
            msg \= f"SAVED: {full}"  
            self.get\_logger().info(f"Auto-save triggered: unknown\_ratio={self.unknown\_ratio:.2f}")  
            self.pub.publish(String(data=msg))  
        except Exception as e:  
            self.pub.publish(String(data=f"ERROR: {e}"))  
   
def main(args=None):  
    rclpy.init(args=args)  
    rclpy.spin(AutoMapSaver())  
    rclpy.shutdown()

### **Solution — Q6: config/hospital\_slam.yaml**

slam\_toolbox:  
  ros\_\_parameters:  
    mode: mapping  
    resolution: 0.03  
    max\_laser\_range: 10.0  
    minimum\_travel\_distance: 0.2  
    minimum\_travel\_heading: 0.15  
    map\_update\_interval: 2.0  
    use\_sim\_time: true  
    scan\_topic: /scan  
    odom\_frame: odom  
    base\_frame: base\_footprint  
    map\_frame: map

# **6\.  EVALUATION SCRIPTS**

pytest-based — unit tests \+ live ROS2 topic/service checks

### **test/evaluate.py — Q1 (Map Monitor)**

\#\!/usr/bin/env python3  
"""Q1 Evaluation: map\_monitor node"""  
import pytest, subprocess, sys  
   
\# ── Unit: cell counting logic ─────────────────────────────────────────  
def count\_cells(data):  
    total   \= len(data)  
    unknown \= sum(1 for c in data if c \== \-1)  
    free    \= sum(1 for c in data if c \== 0\)  
    occ     \= sum(1 for c in data if c \> 0\)  
    known   \= total \- unknown  
    return known, free, occ, unknown  
   
def test\_all\_unknown():  
    k,f,o,u \= count\_cells(\[-1\]\*100)  
    assert k==0 and f==0 and o==0 and u==100  
   
def test\_mixed\_map():  
    data \= \[-1\]\*40 \+ \[0\]\*40 \+ \[50\]\*20  
    k,f,o,u \= count\_cells(data)  
    assert k==60 and f==40 and o==20 and u==40  
   
def test\_free\_plus\_occ\_plus\_unknown\_equals\_total():  
    import random  
    data \= \[random.choice(\[-1,0,50,100\]) for \_ in range(1000)\]  
    k,f,o,u \= count\_cells(data)  
    assert f+o+u \== 1000  
   
\# ── Runtime checks ────────────────────────────────────────────────────  
def test\_map\_stats\_topic\_published():  
    r=subprocess.run(\["ros2","topic","list"\],capture\_output=True,text=True,timeout=10)  
    assert "/map\_stats" in r.stdout  
   
def test\_map\_stats\_type\_is\_string():  
    r=subprocess.run(\["ros2","topic","info","/map\_stats"\],  
        capture\_output=True,text=True,timeout=10)  
    assert "std\_msgs/msg/String" in r.stdout  
   
def test\_slam\_toolbox\_node\_active():  
    r=subprocess.run(\["ros2","node","list"\],capture\_output=True,text=True,timeout=10)  
    assert "slam\_toolbox" in r.stdout  
   
def test\_map\_topic\_published():  
    r=subprocess.run(\["ros2","topic","list"\],capture\_output=True,text=True,timeout=10)  
    assert "/map" in r.stdout  
   
def test\_no\_numpy\_in\_map\_monitor():  
    src=open("src/slam\_starter\_pkg/scripts/map\_monitor.py").read()  
    assert "import numpy" not in src and "from numpy" not in src  
   
def test\_launch\_uses\_yaml\_params\_file():  
    src=open("src/slam\_starter\_pkg/launch/start\_slam.launch.py").read()  
    assert "slam\_params.yaml" in src

### **test/evaluate.py — Q2 (Factory SLAM YAML)**

\#\!/usr/bin/env python3  
"""Q2 Evaluation: factory\_slam.yaml parameter validation"""  
import pytest, yaml  
   
YAML\_PATH \= "src/factory\_slam\_pkg/config/factory\_slam.yaml"  
   
def load\_params():  
    with open(YAML\_PATH) as f:  
        d \= yaml.safe\_load(f)  
    return d\["slam\_toolbox"\]\["ros\_\_parameters"\]  
   
def test\_yaml\_parses\_without\_error():  
    p \= load\_params()  
    assert isinstance(p, dict)  
   
def test\_resolution\_0025():  
    assert abs(load\_params()\["resolution"\] \- 0.025) \< 1e-6  
   
def test\_max\_laser\_range\_8():  
    assert abs(load\_params()\["max\_laser\_range"\] \- 8.0) \< 1e-6  
   
def test\_min\_travel\_distance\_0\_3():  
    assert abs(load\_params()\["minimum\_travel\_distance"\] \- 0.3) \< 1e-6  
   
def test\_min\_travel\_heading\_0\_3():  
    assert abs(load\_params()\["minimum\_travel\_heading"\] \- 0.3) \< 1e-6  
   
def test\_map\_update\_interval\_3():  
    assert abs(load\_params()\["map\_update\_interval"\] \- 3.0) \< 1e-6  
   
def test\_use\_sim\_time\_true():  
    assert load\_params()\["use\_sim\_time"\] \== True  
   
def test\_scan\_topic():  
    assert load\_params()\["scan\_topic"\] \== "/scan"  
   
def test\_frames():  
    p \= load\_params()  
    assert p\["odom\_frame"\]  \== "odom"  
    assert p\["base\_frame"\]  \== "base\_footprint"  
    assert p\["map\_frame"\]   \== "map"  
   
def test\_mode\_mapping():  
    assert load\_params()\["mode"\] \== "mapping"

### **test/evaluate.py — Q5 (Map Diagnostics — comprehensive)**

\#\!/usr/bin/env python3  
"""Q5 Evaluation: map\_diagnostics quality node"""  
import pytest, subprocess, math, re  
   
\# ── Unit: quality classification logic ───────────────────────────────  
def compute\_map\_quality(data, unk\_thresh=0.4):  
    total   \= len(data) or 1  
    unknown \= sum(1 for c in data if c \== \-1)  
    occ     \= sum(1 for c in data if c \> 0\)  
    ur \= unknown/total; or\_ \= occ/total  
    return ("GOOD" if ur \< unk\_thresh else "POOR"), ur, or\_  
   
def compute\_scan\_quality(ranges,rmin,rmax,amin,amax,scan\_thresh=0.8):  
    total=len(ranges) or 1  
    valid=sum(1 for r in ranges if r==r and r\!=float("inf") and rmin\<=r\<=rmax)  
    vr=valid/total  
    cov=(amax-amin)\*180/math.pi  
    return ("GOOD" if vr\>scan\_thresh and cov\>=350.0 else "POOR"), vr, cov  
   
def test\_map\_20pct\_unknown\_is\_good():  
    data=\[-1\]\*200+\[0\]\*500+\[50\]\*300  
    q,ur,\_=compute\_map\_quality(data)  
    assert q=="GOOD" and abs(ur-0.2)\<0.001  
   
def test\_map\_60pct\_unknown\_is\_poor():  
    data=\[-1\]\*600+\[0\]\*400  
    q,ur,\_=compute\_map\_quality(data)  
    assert q=="POOR" and abs(ur-0.6)\<0.001  
   
def test\_scan\_90pct\_valid\_360deg\_is\_good():  
    ranges=\[1.5\]\*360+\[float("inf")\]\*40  
    q,vr,cov=compute\_scan\_quality(ranges,0.1,10.0,  
        \-math.pi,math.pi)  
    assert q=="GOOD"  
   
def test\_scan\_50pct\_inf\_is\_poor():  
    ranges=\[float("inf")\]\*200+\[1.5\]\*200  
    q,vr,\_=compute\_scan\_quality(ranges,0.1,10.0,-math.pi,math.pi)  
    assert q=="POOR"  
   
def test\_overall\_ok\_only\_when\_both\_good():  
    mq="GOOD"; sq="POOR"  
    ov="OK" if mq=="GOOD" and sq=="GOOD" else "DEGRADED"  
    assert ov=="DEGRADED"  
   
def test\_overall\_ok\_when\_both\_good():  
    ov="OK" if "GOOD"=="GOOD" and "GOOD"=="GOOD" else "DEGRADED"  
    assert ov=="OK"  
   
\# ── Runtime ──────────────────────────────────────────────────────────  
def test\_quality\_report\_published():  
    r=subprocess.run(\["ros2","topic","list"\],capture\_output=True,text=True,timeout=10)  
    assert "/map\_quality\_report" in r.stdout  
   
def test\_report\_format():  
    r=subprocess.run(\["ros2","topic","echo","/map\_quality\_report","--once"\],  
        capture\_output=True,text=True,timeout=10)  
    pat=r"map=(GOOD|POOR).\*scan=(GOOD|POOR).\*overall=(OK|DEGRADED)"  
    assert re.search(pat,r.stdout)  
   
def test\_timer\_is\_2\_seconds():  
    src=open("src/map\_diagnostics\_pkg/scripts/map\_diagnostics.py").read()  
    assert "create\_timer(2.0" in src or "create\_timer(2," in src  
   
def test\_no\_numpy():  
    src=open("src/map\_diagnostics\_pkg/scripts/map\_diagnostics.py").read()  
    assert "import numpy" not in src and "from numpy" not in src

### **test/evaluate.py — Q6 (Auto Map Saver — comprehensive)**

\#\!/usr/bin/env python3  
"""Q6 Evaluation: hospital SLAM \+ auto\_map\_saver"""  
import pytest, subprocess, yaml, re, os  
   
YAML  \= "src/hospital\_slam\_pkg/config/hospital\_slam.yaml"  
SCRIPT= "src/hospital\_slam\_pkg/scripts/auto\_map\_saver.py"  
RVIZ  \= "src/hospital\_slam\_pkg/rviz/hospital\_view.rviz"  
LAUNCH= "src/hospital\_slam\_pkg/launch/hospital\_slam.launch.py"  
   
\# ── YAML checks ──────────────────────────────────────────────────────  
def load\_p():  
    with open(YAML) as f: d=yaml.safe\_load(f)  
    return d\["slam\_toolbox"\]\["ros\_\_parameters"\]  
   
def test\_yaml\_resolution\_003():   assert abs(load\_p()\["resolution"\]-0.03)\<1e-6  
def test\_yaml\_max\_range\_10():     assert abs(load\_p()\["max\_laser\_range"\]-10.0)\<1e-6  
def test\_yaml\_travel\_dist\_02():   assert abs(load\_p()\["minimum\_travel\_distance"\]-0.2)\<1e-6  
def test\_yaml\_travel\_head\_015():  assert abs(load\_p()\["minimum\_travel\_heading"\]-0.15)\<1e-6  
def test\_yaml\_update\_interval\_2():assert abs(load\_p()\["map\_update\_interval"\]-2.0)\<1e-6  
def test\_yaml\_mode\_mapping():     assert load\_p()\["mode"\]=="mapping"  
def test\_yaml\_use\_sim\_time():     assert load\_p()\["use\_sim\_time"\]==True  
   
\# ── Script source checks ─────────────────────────────────────────────  
def test\_saved\_guard\_present():  
    src=open(SCRIPT).read()  
    assert "self.saved" in src,"saved guard not found"  
   
def test\_stability\_threshold\_param():  
    src=open(SCRIPT).read()  
    assert "stability\_threshold" in src  
   
def test\_stability\_duration\_param():  
    src=open(SCRIPT).read()  
    assert "stability\_duration" in src  
   
def test\_serialize\_service\_client():  
    src=open(SCRIPT).read()  
    assert "serialize\_map" in src or "SerializePoseGraph" in src  
   
def test\_map\_saver\_cli\_subprocess():  
    src=open(SCRIPT).read()  
    assert "map\_saver\_cli" in src and "subprocess" in src  
   
def test\_no\_numpy():  
    src=open(SCRIPT).read()  
    assert "import numpy" not in src  
   
\# ── RViz config ──────────────────────────────────────────────────────  
def test\_rviz\_four\_displays():  
    src=open(RVIZ).read()  
    for d in \["Map","LaserScan","RobotModel","TF"\]:  
        assert d in src, f"hospital\_view.rviz missing {d}"  
   
\# ── Launch file ──────────────────────────────────────────────────────  
def test\_launch\_refs\_yaml():  
    src=open(LAUNCH).read()  
    assert "hospital\_slam.yaml" in src  
   
def test\_launch\_includes\_all\_nodes():  
    src=open(LAUNCH).read()  
    for n in \["async\_slam\_toolbox\_node","auto\_map\_saver","rviz2"\]:  
        assert n in src, f"Launch missing {n}"  
   
\# ── Runtime ──────────────────────────────────────────────────────────  
def test\_auto\_save\_status\_topic():  
    r=subprocess.run(\["ros2","topic","list"\],capture\_output=True,text=True,timeout=10)  
    assert "/auto\_save\_status" in r.stdout  
   
def test\_status\_sequence():  
    r=subprocess.run(\["ros2","topic","echo","/auto\_save\_status","--once"\],  
        capture\_output=True,text=True,timeout=10)  
    assert any(s in r.stdout for s in \["MONITORING","STABLE","SAVED"\])

# **7\.  judge\_runner.py**

Production-ready  |  Docker-compatible  |  Structured JSON output

\#\!/usr/bin/env python3  
"""  
judge\_runner.py — SLAM Topic  
Usage: python3 judge\_runner.py \--question Q1 \--workspace /home/student/ros2\_ws  
"""  
import argparse,json,os,subprocess,sys,time,signal,logging  
from pathlib import Path  
   
logging.basicConfig(level=logging.INFO,  
    format="\[%(asctime)s\] %(levelname)s — %(message)s")  
log=logging.getLogger("judge\_runner")  
   
Q\_CFG={  
  "Q1":{"pkg":"slam\_starter\_pkg","launch":"start\_slam.launch.py",  
        "tests":"slam\_starter\_pkg/test/evaluate.py",  
        "fns":\["test\_all\_unknown","test\_mixed\_map",  
               "test\_free\_plus\_occ\_plus\_unknown\_equals\_total",  
               "test\_map\_stats\_topic\_published","test\_map\_stats\_type\_is\_string",  
               "test\_slam\_toolbox\_node\_active","test\_map\_topic\_published",  
               "test\_no\_numpy\_in\_map\_monitor","test\_launch\_uses\_yaml\_params\_file"\],  
        "warmup":10,"requires\_launch":True},  
  "Q2":{"pkg":"factory\_slam\_pkg","launch":"factory\_slam.launch.py",  
        "tests":"factory\_slam\_pkg/test/evaluate.py",  
        "fns":\["test\_yaml\_parses\_without\_error","test\_resolution\_0025",  
               "test\_max\_laser\_range\_8","test\_min\_travel\_distance\_0\_3",  
               "test\_min\_travel\_heading\_0\_3","test\_map\_update\_interval\_3",  
               "test\_use\_sim\_time\_true","test\_scan\_topic","test\_frames",  
               "test\_mode\_mapping"\],  
        "warmup":10,"requires\_launch":False},  
  "Q3":{"pkg":"map\_save\_pkg","launch":"save\_map.launch.py",  
        "tests":"map\_save\_pkg/test/evaluate.py",  
        "fns":\["test\_save\_status\_topic","test\_pgm\_created\_after\_trigger",  
               "test\_yaml\_created\_after\_trigger","test\_params\_used",  
               "test\_serialize\_service\_client","test\_error\_branch"\],  
        "warmup":8,"requires\_launch":True},  
  "Q4":{"pkg":"localisation\_pkg","launch":"localise.launch.py",  
        "tests":"localisation\_pkg/test/evaluate.py",  
        "fns":\["test\_params\_mode\_localisation","test\_map\_server\_active",  
               "test\_map\_topic\_published","test\_localization\_node\_executable",  
               "test\_lifecycle\_manager\_in\_launch","test\_rviz\_has\_three\_displays"\],  
        "warmup":12,"requires\_launch":True},  
  "Q5":{"pkg":"map\_diagnostics\_pkg","launch":"diagnostics.launch.py",  
        "tests":"map\_diagnostics\_pkg/test/evaluate.py",  
        "fns":\["test\_map\_20pct\_unknown\_is\_good","test\_map\_60pct\_unknown\_is\_poor",  
               "test\_scan\_90pct\_valid\_360deg\_is\_good","test\_scan\_50pct\_inf\_is\_poor",  
               "test\_overall\_ok\_only\_when\_both\_good","test\_overall\_ok\_when\_both\_good",  
               "test\_quality\_report\_published","test\_report\_format",  
               "test\_timer\_is\_2\_seconds","test\_no\_numpy"\],  
        "warmup":8,"requires\_launch":True},  
  "Q6":{"pkg":"hospital\_slam\_pkg","launch":"hospital\_slam.launch.py",  
        "tests":"hospital\_slam\_pkg/test/evaluate.py",  
        "fns":\["test\_yaml\_resolution\_003","test\_yaml\_max\_range\_10",  
               "test\_yaml\_travel\_dist\_02","test\_yaml\_travel\_head\_015",  
               "test\_yaml\_update\_interval\_2","test\_yaml\_mode\_mapping",  
               "test\_yaml\_use\_sim\_time","test\_saved\_guard\_present",  
               "test\_stability\_threshold\_param","test\_stability\_duration\_param",  
               "test\_serialize\_service\_client","test\_map\_saver\_cli\_subprocess",  
               "test\_no\_numpy","test\_rviz\_four\_displays",  
               "test\_launch\_refs\_yaml","test\_launch\_includes\_all\_nodes",  
               "test\_auto\_save\_status\_topic","test\_status\_sequence"\],  
        "warmup":15,"requires\_launch":True},  
}  
   
def build\_ws(ws,env):  
    r=subprocess.run(\["colcon","build","--symlink-install"\],  
        env=env,capture\_output=True,text=True,timeout=240,cwd=ws)  
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
    env=os.environ.copy(); env\["ROS\_DOMAIN\_ID"\]="88"  
    bld=build\_ws(workspace,env)  
    out\["build"\]=bld  
    if not bld\["success"\]:  
        out.update({"status":"build\_failed","message":"Build failed"}); return out  
    env\_s=source\_ws(workspace)  
    proc=None  
    if cfg\["requires\_launch"\]:"  
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
| ES-01 | Q1 | Student launches async node but forgets use\_sim\_time | Map builds but timestamps diverge — TF errors in RViz | Runtime: ros2 param get /slam\_toolbox use\_sim\_time |
| ES-02 | Q1 | map\_monitor uses numpy.where for cell counting | test\_no\_numpy\_in\_map\_monitor fails | Source import scan |
| ES-03 | Q1 | known\_cells defined as total not total-unknown | Injected 40% unknown map returns wrong known count | Unit test with known data fixture |
| ES-04 | Q2 | resolution set to 0.05 not 0.025 | test\_resolution\_0025 fails | YAML parse \+ float comparison 1e-6 |
| ES-05 | Q2 | YAML has params under wrong key (e.g. "slam" not "slam\_toolbox") | test\_yaml\_parses\_without\_error passes but all param tests fail | Nested key navigation check |
| ES-06 | Q3 | map\_saver\_cli called but path missing map\_output\_dir param | Files saved to wrong directory; path evaluator checks fail | os.path.exists for expected output path |
| ES-07 | Q3 | SerializePoseGraph service not called — only subprocess | test\_serialize\_service\_client fails | Source scan for create\_client \+ SerializePoseGraph |
| ES-08 | Q4 | mode set to mapping instead of localization | test\_params\_mode\_localisation fails immediately | YAML key value check |
| ES-09 | Q4 | lifecycle\_manager omitted from launch — map\_server never transitions | map\_server starts but /map never published | Source scan for lifecycle\_manager \+ runtime /map check |
| ES-10 | Q5 | angular\_coverage computed in radians not degrees | 350-degree scan produces coverage=6.1 → POOR instead of GOOD | Unit test: 360deg scan must return GOOD scan\_quality |
| ES-11 | Q5 | Timer set to 0.5 not 2.0 (period=0.5 Hz not 0.5 Hz) | test\_timer\_is\_2\_seconds fails (common confusion of freq/period) | Source scan: create\_timer value check |
| ES-12 | Q6 | saved guard missing — \_do\_save fires on every timer tick | Map saved repeatedly; disk fills; second save corrupts first | Runtime: count /auto\_save\_status "SAVED" messages \> 1 → fail |
| ES-13 | Q6 | stable\_since never reset when ratio rises above threshold | Instability period wrongly counted toward stability duration | Unit sim: inject ratio above threshold mid-sequence → verify reset |
| ES-14 | Q6 | hospital\_slam.yaml missing minimum\_travel\_heading param | test\_yaml\_travel\_head\_015 fails | YAML key existence \+ value check |
| ES-15 | Q6 | hospital\_view.rviz missing TF display | test\_rviz\_four\_displays fails | Source text scan for "TF" class in rviz YAML |

# **9\.  COMMON MISTAKES & DEBUGGING NOTES**

Per-question error patterns with root causes and fixes

### **Q1 — Launch SLAM Toolbox \+ Map Monitor**

| Mistake | Symptom | Fix |
| ----- | ----- | ----- |
| use\_sim\_time not set on slam\_toolbox node | TF timestamps diverge from simulated time — RViz shows stale or missing transforms | Pass {"use\_sim\_time": True} as a parameter alongside the YAML file |
| map\_monitor uses msg.data as-is without list() | Iterating over a raw OccupancyGrid data field returns bytes not ints in some ROS2 builds | Always call list(msg.data) before iterating |
| Launching RViz before SLAM Toolbox is ready | RViz opens with "Waiting for message" on the Map display for 30+ seconds | Add slam\_toolbox to the LaunchDescription first; or add a launch\_ros.actions.timer |

### **Q2 — SLAM Configuration YAML**

| Mistake | Symptom | Fix |
| ----- | ----- | ----- |
| YAML indented under wrong parent key | All values parse as None — slam\_toolbox silently uses defaults | Structure must be: slam\_toolbox: → ros\_\_parameters: → \<param\>: value (two nesting levels) |
| resolution written as integer 0 instead of float 0.025 | YAML parses as 0 — slam\_toolbox generates an unusably coarse 0-resolution map | Always write floats explicitly: resolution: 0.025 not resolution: .025 or 0 |
| params\_file path is absolute /home/user/... not package-relative | Works on developer machine; fails in Docker container | Use get\_package\_share\_directory() \+ os.path.join() — never hardcode absolute paths |

### **Q3 — Map Save Node**

| Mistake | Symptom | Fix |
| ----- | ----- | ----- |
| subprocess.run without check=True | map\_saver\_cli fails silently — status published as SAVED even when .pgm not created | Always pass check=True so subprocess raises on non-zero exit code |
| SerializePoseGraph service called before slam\_toolbox is ready | Service call returns UNAVAILABLE or hangs | Add self.cli.wait\_for\_service(timeout\_sec=5.0) before calling call\_async |
| map\_name param not declared before reading it | ParameterNotDeclaredException at startup | declare\_parameter() must always precede get\_parameter() in \_\_init\_\_ |

### **Q4 — Localisation Stack**

| Mistake | Symptom | Fix |
| ----- | ----- | ----- |
| Using async\_slam\_toolbox\_node instead of localization\_slam\_toolbox\_node | slam\_toolbox starts in mapping mode — /map grows instead of staying fixed | Localisation requires localization\_slam\_toolbox\_node executable |
| lifecycle\_manager omitted from launch | map\_server starts but never transitions to Active state — /map never published | Add lifecycle\_manager node with autostart: True and node\_names: \["map\_server"\] |
| map\_file\_name has .yaml extension in localise\_params.yaml | slam\_toolbox looks for warehouse\_map.yaml.data — cannot find serialised file | map\_file\_name must be path WITHOUT extension: maps/warehouse\_map (no .yaml) |

### **Q5 — Map Quality Diagnostics**

| Mistake | Symptom | Fix |
| ----- | ----- | ----- |
| angular\_coverage computed in radians not converted to degrees | 360° scan produces coverage ≈ 6.28 — POOR scan quality returned incorrectly | coverage\_deg \= (angle\_max \- angle\_min) \* 180.0 / math.pi  — must multiply by 180/π |
| Timer period \= 0.5 (meaning 2 Hz) — student confused period and frequency | test\_timer\_is\_2\_seconds fails — create\_timer(0.5) fires at 2 Hz not 0.5 Hz | create\_timer(2.0, callback) — period is in seconds; 2.0 s period \= 0.5 Hz |
| No default values for ratios before first message arrives | Division by zero on timer\_cb before any /map received | Initialise self.unknown\_ratio \= 1.0 and self.valid\_ratio \= 0.0 in \_\_init\_\_ |

### **Q6 — Auto Map Saver (Full Pipeline)**

| Mistake | Symptom | Fix |
| ----- | ----- | ----- |
| Missing self.saved guard flag | \_do\_save fires on every timer tick once stable — map saved hundreds of times | Add self.saved \= False; set True in \_do\_save; guard with if self.saved: return at top of timer\_cb |
| stable\_since never reset when unknown\_ratio rises above threshold | A momentary degradation is ignored — stability timer continues running | In map\_cb: if ratio \>= threshold: self.stable\_since \= None  (reset the timer) |
| Using time.time() instead of ROS2 clock for stability timing | Stability check breaks with use\_sim\_time=True — wall clock and sim clock diverge | Use self.get\_clock().now().nanoseconds \* 1e-9 for all time tracking |
| hospital\_slam.yaml has mode: localization not mapping | No new map cells generated — map stays empty | Q6 builds a NEW map: mode must be mapping |

| General SLAM Toolbox Debugging Notes |
| :---- |
| **No /map publishing:** Check slam\_toolbox is subscribed to /scan with ros2 topic echo /scan first. If /scan is empty, the Gazebo LiDAR plugin topic name may not match scan\_topic in the YAML. |
| **TF error "map→odom not found":** slam\_toolbox publishes the map→odom transform. If this is missing, slam\_toolbox failed to initialise. Check the node log: ros2 node info /slam\_toolbox |
| **Localisation mode map not loading:** map\_file\_name must point to the .data/.posegraph files WITHOUT extension. The file path must be accessible inside the container. |
| **map\_saver\_cli produces empty .pgm:** The /map topic must be actively publishing when map\_saver\_cli runs. Ensure slam\_toolbox is still running when the save is triggered. |
| **lifecycle\_manager vs map\_server:** In ROS2 Nav2, map\_server is a lifecycle node. It will not start publishing until the lifecycle\_manager transitions it to the Active state. |
| **Resolution mismatch in /map:** If the loaded map resolution differs from the YAML, slam\_toolbox uses the serialised file's resolution. Re-save the map after changing resolution. |

**✓ All 10 syllabus skills covered   |   ✓ All 6 questions auto-gradable   |   ✓ ROS2 Humble / SLAM Toolbox compatible**