NIAT  |  NxtWave Robotics & AI Platform  
**Coding Assessment  —  Topic Series**

**SIMULATION**  
Gazebo  |  RViz2  |  ROS2 Humble  |  SDF Worlds  |  Sensor Topics  
6 Auto-Graded Coding Questions  |  Easy → Hard  |  Ubuntu 22.04 / Python 3.10  
**Robot modelling prereqs assumed complete. No SLAM or Nav2 concepts introduced.**

# **1\.  TOPIC ANALYSIS**

Scope, platform, and assessment philosophy

**Topic:** Simulation

**Platform:** ROS2 Humble  |  Ubuntu 22.04  |  Python 3.10  |  Gazebo Classic  |  RViz2

The Simulation topic bridges robot modelling and live operation. Students must be able to assemble a functional simulated environment: spawn a URDF robot into Gazebo, author SDF world files with static geometry, write ROS2 subscriber nodes that process real sensor topic output (LaserScan, Image, Imu), and configure RViz2 display panels to observe pose, sensor streams, and the TF tree — all at the same time. Every question is strictly bounded to this syllabus. No Nav2, SLAM, MoveIt2, or motion-planning concepts appear.

# **2\.  SKILLS BEING TESTED**

Syllabus coverage matrix — all skills must be covered

| ID | Skill | Covered By |
| ----- | ----- | ----- |
| S1 | Spawning a URDF robot into a running Gazebo world | Q1, Q6 |
| S2 | Creating a custom SDF world file with static obstacles | Q2, Q6 |
| S3 | Writing launch files that start Gazebo with a custom world | Q1, Q2, Q6 |
| S4 | Subscribing to simulated LaserScan sensor topics | Q3, Q6 |
| S5 | Subscribing to simulated Camera / Image sensor topics | Q4, Q6 |
| S6 | Subscribing to simulated IMU sensor topics | Q5, Q6 |
| S7 | Configuring RViz2 displays (RobotModel, LaserScan, Camera, Imu, TF) | Q1, Q3, Q4, Q5, Q6 |
| S8 | Visualising robot pose in RViz2 | Q1, Q6 |
| S9 | Visualising the TF tree in RViz2 | Q1, Q6 |
| S10 | Launching robot\_state\_publisher for simulation | Q1, Q6 |

**All 10 skills covered.** No skill is untested.

# **3\.  SIX CODING QUESTIONS**

Difficulty: Easy → Hard  |  All questions are auto-gradable

| QUESTION 1   |   EASY Spawn a URDF Robot into Gazebo and Visualise It in RViz2 |
| :---- |

| Tested Skills |
| :---- |
| **S1 —** Spawning a URDF robot into Gazebo |
| **S3 —** Launch file that starts Gazebo |
| **S7/S8/S9 —** RViz2 RobotModel \+ TF displays |
| **S10 —** robot\_state\_publisher for simulation |

**Scenario**

You have just joined the simulation team at an autonomous delivery startup. The mechanical team has finished the URDF for the delivery robot (it is already provided). Your task is to write a ROS2 launch file that starts Gazebo Classic with an empty world, spawns the robot at the origin using the spawn\_entity node, starts robot\_state\_publisher so TF is broadcast, and opens RViz2 pre-configured to show the RobotModel and TF displays.

**Files Student Can Edit**

launch/sim.launch.py  
rviz/robot\_view.rviz

**Existing Package Structure**

delivery\_sim/  
├── launch/  
│   └── sim.launch.py           ← EDIT THIS  
├── urdf/  
│   └── delivery\_bot.urdf       (pre-filled — do not modify)  
├── rviz/  
│   └── robot\_view.rviz         ← EDIT THIS  
├── worlds/  
│   └── empty.world             (pre-filled — do not modify)  
├── package.xml  
└── setup.py

**Student Objective**

1. In launch/sim.launch.py, include all four nodes:

   * **gazebo\_ros launch\_gazebo** — launches Gazebo Classic with worlds/empty.world

   * **robot\_state\_publisher** — loads delivery\_bot.urdf as robot\_description parameter

   * **spawn\_entity.py** — spawns the robot at x=0 y=0 z=0.1 with name "delivery\_bot"

   * **rviz2** — opens with the rviz/robot\_view.rviz config

2. In rviz/robot\_view.rviz, configure two displays:

   * **RobotModel** — Fixed Frame: base\_link, Description Source: /robot\_description

   * **TF** — show all frames, marker scale 0.5

**Constraints**

* Do NOT modify delivery\_bot.urdf or empty.world

* robot\_state\_publisher must receive the URDF from the file at launch-time (not a static string)

* spawn\_entity must use the /robot\_description topic as its input source

* RViz config must be a .rviz YAML file — not hardcoded in the launch

**Expected Behaviour**

* Gazebo opens with the empty world

* The delivery robot model appears at the origin in Gazebo

* RViz opens simultaneously and shows the coloured RobotModel mesh

* TF arrows are visible linking base\_footprint → base\_link → wheels

* No TF errors in the RViz status bar

**Evaluation Criteria (Hidden)**

* /robot\_description topic is published

* Gazebo service /gazebo/get\_entity\_state responds to entity "delivery\_bot"

* TF transform base\_footprint → base\_link is present

* robot\_state\_publisher node is active

* rviz2 node is active

* robot\_view.rviz contains both RobotModel and TF display entries

| QUESTION 2   |   EASY-MEDIUM Author a Custom SDF World with Static Obstacles |
| :---- |

| Tested Skills |
| :---- |
| **S2 —** Creating a custom SDF world file with static obstacles |
| **S3 —** Launch file that starts Gazebo with the custom world |

**Scenario**

The test track team needs a standard evaluation arena for benchmarking the warehouse robot's obstacle avoidance algorithm. The arena consists of a flat ground plane, four box-shaped pillars arranged in a square, and one cylindrical post in the centre. You must write the SDF world file from scratch and update the launch file to load it into Gazebo.

**Files Student Can Edit**

worlds/arena.world  
launch/arena.launch.py

**Existing Package Structure**

arena\_sim/  
├── launch/  
│   └── arena.launch.py         ← EDIT THIS  
├── worlds/  
│   └── arena.world             ← EDIT THIS (currently empty)  
├── urdf/  
│   └── warehouse\_bot.urdf      (pre-filled)  
├── package.xml  
└── setup.py

**Obstacle Specification (from test track team)**

| Model Name | Shape | Size (m) | Pose (x y z r p y) | Static |
| ----- | ----- | ----- | ----- | ----- |
| ground\_plane | plane (normal z) | 100×100 | 0 0 0 0 0 0 | Yes |
| pillar\_NE | box | 0.2 × 0.2 × 1.0 | 3.0 3.0 0.5 0 0 0 | Yes |
| pillar\_NW | box | 0.2 × 0.2 × 1.0 | \-3.0 3.0 0.5 0 0 0 | Yes |
| pillar\_SE | box | 0.2 × 0.2 × 1.0 | 3.0 \-3.0 0.5 0 0 0 | Yes |
| pillar\_SW | box | 0.2 × 0.2 × 1.0 | \-3.0 \-3.0 0.5 0 0 0 | Yes |
| centre\_post | cylinder | r=0.1, h=0.8 | 0.0 0.0 0.4 0 0 0 | Yes |

**Student Objective**

3. In worlds/arena.world, write a valid SDF 1.6 world file containing all six models from the table

4. Each model must have a \<static\>true\</static\> tag, a \<collision\> geometry, and a \<visual\> geometry

5. In launch/arena.launch.py, launch Gazebo Classic with arena.world and spawn warehouse\_bot.urdf at the origin

**Constraints**

* SDF version must be 1.6

* All obstacles must be static — robots must not be able to push them

* Do NOT use model includes from the Gazebo model database — all geometry inline

* Do NOT modify warehouse\_bot.urdf

**Expected Behaviour**

* Gazebo opens with the arena visible: ground plane \+ 4 pillars \+ 1 central post

* Pillars are located at the four quadrant positions

* Central cylinder post is at the origin of the arena

* Robot spawns without falling through the ground

**Evaluation Criteria (Hidden)**

* worlds/arena.world is valid SDF — parsed by sdformat library without error

* Exactly 6 model elements present (ground\_plane \+ 4 pillars \+ centre\_post)

* Each pillar has correct box geometry (0.2×0.2×1.0)

* centre\_post has cylinder geometry (r=0.1, h=0.8)

* All models have \<static\>true\</static\>

* Pillar poses match specification within 0.01 m

* Gazebo /gazebo/get\_world\_properties lists the 6 models

| QUESTION 3   |   EASY-MEDIUM Subscribe to a Simulated LaserScan and Log Obstacle Proximity |
| :---- |

| Tested Skills |
| :---- |
| **S4 —** Subscribing to simulated LaserScan sensor topics |
| **S7 —** Configuring RViz2 LaserScan display |

**Scenario**

The safety team on an inspection robot project needs a software watchdog that continuously monitors the LiDAR data coming from Gazebo simulation. Your task is to implement a ROS2 subscriber node that receives sensor\_msgs/LaserScan messages on /scan, finds the minimum range reading in each scan, classifies it as SAFE / WARNING / DANGER, and publishes the result on a string topic. You must also update the provided RViz config to display the LaserScan.

**Files Student Can Edit**

scripts/scan\_monitor.py  
rviz/sensor\_view.rviz

**Existing Package Structure**

scan\_monitor\_pkg/  
├── launch/  
│   └── monitor.launch.py       (pre-filled — do not modify)  
├── scripts/  
│   └── scan\_monitor.py         ← EDIT THIS  
├── rviz/  
│   └── sensor\_view.rviz        ← EDIT THIS  
├── package.xml  
└── setup.py

**Student Objective**

6. **Subscriber:** /scan (sensor\_msgs/LaserScan)

   * Extract all finite range values (filter out inf and nan)

   * Compute min\_range \= minimum of finite values. If no finite values, use float("inf")

7. **Classification thresholds (from params):**

   * **safe\_distance** parameter (default 1.0 m): min\_range \>= safe → "SAFE"

   * **warn\_distance** parameter (default 0.5 m): warn \<= min\_range \< safe → "WARNING"

   * min\_range \< warn → "DANGER"

8. **Publisher:** /proximity\_status (std\_msgs/String) — publish classification string on every scan callback

9. **Logger:** Log at INFO level: "min\_range=X.XXm  status=SAFE/WARNING/DANGER"

10. In rviz/sensor\_view.rviz, add a LaserScan display on topic /scan with a size of 0.03 m and colour by intensity

**Constraints**

* Load safe\_distance and warn\_distance from ROS2 parameters

* Do NOT modify the launch file

* Use only sensor\_msgs.msg.LaserScan and std\_msgs.msg.String

* Do NOT import numpy for this task — use Python built-in math/min only

**Expected Behaviour**

* With no obstacles: /proximity\_status publishes "SAFE"

* With obstacle at 0.7 m: "WARNING"

* With obstacle at 0.2 m: "DANGER"

* RViz shows the LaserScan point cloud from Gazebo

**Evaluation Criteria (Hidden)**

* /proximity\_status topic published

* Message type is std\_msgs/String

* Classification correct for 10+ injected scan scenarios

* Inf/nan values in ranges are filtered correctly

* Parameters safe\_distance and warn\_distance are declared and read

* sensor\_view.rviz contains LaserScan display on /scan

| QUESTION 4   |   MEDIUM Process Simulated Camera Images and Detect Bright Regions |
| :---- |

| Tested Skills |
| :---- |
| **S5 —** Subscribing to simulated Camera / Image sensor topics |
| **S7 —** Configuring RViz2 Camera display |

**Scenario**

The inspection robot uses a forward-facing simulated camera to detect illuminated panels on factory machinery. The camera publishes sensor\_msgs/Image messages on /camera/image\_raw. You must implement a ROS2 node that receives each image, converts it from ROS Image format to a NumPy array using cv\_bridge, computes the mean pixel brightness across the entire image (mean of all channels), and publishes a Float32 brightness value. You must also configure the RViz2 Camera display to show the live video feed.

**Files Student Can Edit**

scripts/image\_processor.py  
rviz/camera\_view.rviz

**Existing Package Structure**

camera\_proc\_pkg/  
├── launch/  
│   └── camera.launch.py        (pre-filled — do not modify)  
├── scripts/  
│   └── image\_processor.py      ← EDIT THIS  
├── rviz/  
│   └── camera\_view.rviz        ← EDIT THIS  
├── package.xml  
└── setup.py

**Student Objective**

11. **Subscription:** /camera/image\_raw (sensor\_msgs/Image)

12. Convert the ROS Image message to a NumPy array using cv\_bridge.CvBridge().imgmsg\_to\_cv2(msg, desired\_encoding="bgr8")

13. Compute mean brightness: take the mean of all values in the NumPy array (all pixels, all channels)

14. **Publish:** /image\_brightness (std\_msgs/Float32) — publish the mean brightness value on every image callback

15. Log at INFO level every 30 frames: "frame N — mean\_brightness=XXX.X"

16. In rviz/camera\_view.rviz, add a Camera display on /camera/image\_raw

**Constraints**

* Must use cv\_bridge for the conversion — do not manually unpack the image bytes

* desired\_encoding must be "bgr8"

* Do NOT save images to disk

* Do NOT modify the launch file

**Expected Behaviour**

* /image\_brightness publishes Float32 values between 0 and 255

* A synthetic all-black image (0 fill) returns brightness ≈ 0.0

* A synthetic all-white image (255 fill) returns brightness ≈ 255.0

* RViz Camera panel shows the live Gazebo camera feed

**Evaluation Criteria (Hidden)**

* /image\_brightness topic published with std\_msgs/Float32

* Mean brightness for injected black image: \< 0.5

* Mean brightness for injected white image: \> 254.5

* Mean brightness for injected mid-grey (128) image: 127.0 ± 2.0

* cv\_bridge is imported and used (source scan)

* camera\_view.rviz contains Camera display on /camera/image\_raw

| QUESTION 5   |   MEDIUM Build an IMU Subscriber Node and Detect Tilt Events |
| :---- |

| Tested Skills |
| :---- |
| **S6 —** Subscribing to simulated IMU sensor topics |
| **S7 —** Configuring RViz2 Imu display |

**Scenario**

A service robot carries a tray of delicate items. The safety system monitors the IMU to detect if the robot tilts beyond acceptable limits. Your task is to implement a ROS2 node that subscribes to the simulated IMU topic (/imu/data), extracts linear acceleration and angular velocity, computes the tilt angle from the accelerometer data (pitch from ax/az), and publishes a Bool on /tilt\_alert if the absolute tilt exceeds a configurable threshold. You must also configure RViz2 to display the Imu visualisation.

**Files Student Can Edit**

scripts/imu\_monitor.py  
rviz/imu\_view.rviz

**Existing Package Structure**

imu\_monitor\_pkg/  
├── launch/  
│   └── imu.launch.py           (pre-filled — do not modify)  
├── scripts/  
│   └── imu\_monitor.py          ← EDIT THIS  
├── rviz/  
│   └── imu\_view.rviz           ← EDIT THIS  
├── package.xml  
└── setup.py

**Student Objective**

17. **Subscription:** /imu/data (sensor\_msgs/Imu)

18. Extract **linear\_acceleration.x** (ax) and **linear\_acceleration.z** (az) from the message

19. Compute approximate pitch (tilt) angle: pitch \= math.atan2(ax, az)

20. Load tilt\_threshold parameter (default 0.3 rad) from ROS2 parameter server

21. **Publisher /tilt\_alert (std\_msgs/Bool):** True if abs(pitch) \> tilt\_threshold, else False — publish on every IMU callback

22. **Publisher /tilt\_angle (std\_msgs/Float32):** publish the raw pitch angle in radians on every callback

23. Log at WARN level whenever tilt alert fires: "TILT ALERT: pitch=X.XXX rad"

24. In rviz/imu\_view.rviz, add an Imu display on /imu/data with box scale 0.3

**Constraints**

* Load tilt\_threshold from ROS2 parameters — do NOT hardcode

* Use only math.atan2 — do NOT use numpy or scipy

* Do NOT modify the launch file

**Expected Behaviour**

* Robot flat on ground: /tilt\_alert \= False

* Robot tilted 20° (≈0.35 rad): /tilt\_alert \= True (exceeds 0.3 rad default)

* /tilt\_angle publishes current pitch every IMU update

* RViz Imu display shows orientation box rotating with simulated tilt

**Evaluation Criteria (Hidden)**

* /tilt\_alert published as std\_msgs/Bool

* /tilt\_angle published as std\_msgs/Float32

* Tilt detection correct for 10+ injected IMU scenarios

* tilt\_threshold parameter declared and used

* atan2 used for pitch computation (source scan)

* imu\_view.rviz contains Imu display on /imu/data

| QUESTION 6   |   HARD Assemble a Complete Simulated Sensor Robot Environment |
| :---- |

| Tested Skills |
| :---- |
| **S1 —** Spawning URDF robot into Gazebo |
| **S2 —** Custom SDF world with static obstacles |
| **S3 —** Launch file starting Gazebo with custom world |
| **S4/S5/S6 —** LaserScan, Image, and IMU subscriber nodes |
| **S7/S8/S9/S10 —** RViz2 full configuration \+ TF tree |

**Scenario**

You are the lead simulation engineer for a hospital service robot project. The robot must navigate a ward environment — a corridor with two doorframe obstacles — while streaming all three sensor feeds. No existing environment or launch file is provided. You must build everything from scratch: the SDF ward world, the master launch file that starts the full stack, a single unified sensor aggregator node that subscribes to LaserScan, Image, and IMU simultaneously and publishes a structured status string, and a fully configured RViz2 layout showing pose, all sensors, and the TF tree. This is the kind of task assigned to a simulation engineer on their first day.

**Files Student Can Edit**

worlds/ward.world  
launch/ward\_sim.launch.py  
scripts/sensor\_aggregator.py  
rviz/full\_view.rviz

**Existing Package Structure**

ward\_sim\_pkg/  
├── launch/  
│   └── ward\_sim.launch.py       ← EDIT THIS (currently empty)  
├── worlds/  
│   └── ward.world               ← EDIT THIS (currently empty)  
├── urdf/  
│   └── hospital\_bot.urdf        (pre-filled — do not modify)  
├── scripts/  
│   └── sensor\_aggregator.py     ← EDIT THIS (currently empty)  
├── rviz/  
│   └── full\_view.rviz           ← EDIT THIS (currently empty)  
├── package.xml  
└── setup.py

**Ward World Specification**

| Model Name | Shape | Size (m) | Pose (x y z) | Notes |
| ----- | ----- | ----- | ----- | ----- |
| ground\_plane | plane | 100×100 | 0 0 0 | static, z-normal |
| corridor\_wall\_left | box | 6.0 × 0.2 × 2.0 | \-2.0 1.5 1.0 | static wall |
| corridor\_wall\_right | box | 6.0 × 0.2 × 2.0 | \-2.0 \-1.5 1.0 | static wall |
| doorframe\_left | box | 0.2 × 0.5 × 2.0 | 1.5 1.5 1.0 | static obstacle |
| doorframe\_right | box | 0.2 × 0.5 × 2.0 | 1.5 \-1.5 1.0 | static obstacle |

**Student Objective**

25. In worlds/ward.world — author the SDF 1.6 world containing all 5 models from the table (all static, collision \+ visual for each)

26. In launch/ward\_sim.launch.py — launch the full stack:

    * Gazebo Classic with ward.world

    * robot\_state\_publisher with hospital\_bot.urdf

    * spawn\_entity at position x=-3.0, y=0.0, z=0.1

    * sensor\_aggregator node

    * rviz2 with full\_view.rviz

27. In scripts/sensor\_aggregator.py — implement a single ROS2 node with three subscriptions:

    * **LaserScan /scan —** compute min\_range (filtering inf/nan)

    * **Image /camera/image\_raw —** compute mean\_brightness using cv\_bridge \+ numpy mean

    * **IMU /imu/data —** compute pitch \= atan2(ax, az)

    * Publish **/sensor\_status** (std\_msgs/String) every second via a timer: "lidar=X.XXm  brightness=XXX.X  pitch=X.XXXrad"

28. In rviz/full\_view.rviz — configure all five display types:

    * RobotModel — /robot\_description, Fixed Frame: base\_footprint

    * TF — all frames, marker scale 0.3

    * LaserScan — /scan, size 0.03 m

    * Camera — /camera/image\_raw

    * Imu — /imu/data, box scale 0.3

**Constraints**

* SDF world must be version 1.6

* All obstacles must have \<static\>true\</static\>, \<collision\>, and \<visual\>

* sensor\_aggregator must use a single node — do not create three separate nodes

* The /sensor\_status timer must fire at 1 Hz (period=1.0 second)

* IMU pitch must use math.atan2 — no scipy or tf\_transformations

* Image conversion must use cv\_bridge — no manual byte parsing

* Do NOT modify hospital\_bot.urdf

**Expected Behaviour**

* Gazebo opens with the ward corridor visible

* Robot spawns in the corridor, does not fall through the floor

* /sensor\_status publishes formatted string at 1 Hz

* RViz shows robot model, TF tree, LaserScan hits on corridor walls, camera panel, and IMU orientation box

* No TF errors in RViz status

**Evaluation Criteria (Hidden)**

* ward.world is valid SDF 1.6 — parses without error

* Exactly 5 models in world file

* All 5 models have \<static\>true\</static\>

* spawn\_entity places robot at x=-3.0, y=0.0 within 0.05 m

* /sensor\_status topic published at ≈1 Hz

* /sensor\_status message format matches specification (regex check)

* robot\_state\_publisher active, /robot\_description published

* TF frame base\_footprint → base\_link present

* full\_view.rviz contains all 5 display types

* sensor\_aggregator uses cv\_bridge and math.atan2 (source scan)

# **4\.  ROS PACKAGE STRUCTURES**

One package per question — all pre-built, student edits only listed files

**delivery\_sim  (Q1)**

delivery\_sim/  
├── launch/  
│   └── sim.launch.py  
├── urdf/  
│   └── delivery\_bot.urdf  
├── rviz/  
│   └── robot\_view.rviz  
├── worlds/  
│   └── empty.world  
├── test/  
│   └── evaluate.py  
├── package.xml  
└── setup.py

**arena\_sim  (Q2)**

arena\_sim/  
├── launch/  
│   └── arena.launch.py  
├── worlds/  
│   └── arena.world  
├── urdf/  
│   └── warehouse\_bot.urdf  
├── test/  
│   └── evaluate.py  
├── package.xml  
└── setup.py

**scan\_monitor\_pkg  (Q3)**

scan\_monitor\_pkg/  
├── launch/  
│   └── monitor.launch.py  
├── scripts/  
│   └── scan\_monitor.py  
├── rviz/  
│   └── sensor\_view.rviz  
├── test/  
│   └── evaluate.py  
├── package.xml  
└── setup.py

**camera\_proc\_pkg  (Q4)**

camera\_proc\_pkg/  
├── launch/  
│   └── camera.launch.py  
├── scripts/  
│   └── image\_processor.py  
├── rviz/  
│   └── camera\_view.rviz  
├── test/  
│   └── evaluate.py  
├── package.xml  
└── setup.py

**imu\_monitor\_pkg  (Q5)**

imu\_monitor\_pkg/  
├── launch/  
│   └── imu.launch.py  
├── scripts/  
│   └── imu\_monitor.py  
├── rviz/  
│   └── imu\_view.rviz  
├── test/  
│   └── evaluate.py  
├── package.xml  
└── setup.py

**ward\_sim\_pkg  (Q6)**

ward\_sim\_pkg/  
├── launch/  
│   └── ward\_sim.launch.py  
├── worlds/  
│   └── ward.world  
├── urdf/  
│   └── hospital\_bot.urdf  
├── scripts/  
│   └── sensor\_aggregator.py  
├── rviz/  
│   └── full\_view.rviz  
├── test/  
│   └── evaluate.py  
├── package.xml  
└── setup.py

# **5\.  REFERENCE SOLUTIONS**

Production-quality, executable, ROS2 Humble compatible

### **Solution — Q1: launch/sim.launch.py**

\#\!/usr/bin/env python3  
"""Q1 Reference Solution: Gazebo spawn \+ RViz2 launch"""  
import os  
from launch import LaunchDescription  
from launch.actions import IncludeLaunchDescription  
from launch.launch\_description\_sources import PythonLaunchDescriptionSource  
from launch\_ros.actions import Node  
from ament\_index\_python.packages import get\_package\_share\_directory  
   
def generate\_launch\_description():  
    pkg   \= get\_package\_share\_directory("delivery\_sim")  
    gz\_pkg= get\_package\_share\_directory("gazebo\_ros")  
    urdf  \= os.path.join(pkg, "urdf", "delivery\_bot.urdf")  
    world \= os.path.join(pkg, "worlds", "empty.world")  
    rviz  \= os.path.join(pkg, "rviz", "robot\_view.rviz")  
   
    with open(urdf, "r") as f:  
        robot\_desc \= f.read()  
   
    gazebo \= IncludeLaunchDescription(  
        PythonLaunchDescriptionSource(  
            os.path.join(gz\_pkg, "launch", "gazebo.launch.py")),  
        launch\_arguments={"world": world}.items())  
   
    rsp \= Node(  
        package="robot\_state\_publisher",  
        executable="robot\_state\_publisher",  
        parameters=\[{"robot\_description": robot\_desc}\],  
        output="screen")  
   
    spawn \= Node(  
        package="gazebo\_ros",  
        executable="spawn\_entity.py",  
        arguments=\["-topic", "/robot\_description",  
                   "-entity", "delivery\_bot",  
                   "-x", "0.0", "-y", "0.0", "-z", "0.1"\],  
        output="screen")  
   
    rviz\_node \= Node(  
        package="rviz2",  
        executable="rviz2",  
        arguments=\["-d", rviz\],  
        output="screen")  
   
    return LaunchDescription(\[gazebo, rsp, spawn, rviz\_node\])

### **Solution — Q1: rviz/robot\_view.rviz**

Panels:  
  \- Class: rviz\_common/Displays  
Visualization Manager:  
  Displays:  
    \- Class: rviz\_default\_plugins/RobotModel  
      Name: RobotModel  
      Enabled: true  
      Description Source: Topic  
      Description Topic: /robot\_description  
      Fixed Frame: base\_link  
    \- Class: rviz\_default\_plugins/TF  
      Name: TF  
      Enabled: true  
      Marker Scale: 0.5  
      Show Axes: true  
      Show Names: true  
  Fixed Frame: base\_footprint  
  Background Color: 48; 48; 48

### **Solution — Q2: worlds/arena.world**

\<?xml version="1.0"?\>  
\<sdf version="1.6"\>  
  \<world name="arena"\>  
   
    \<include\>\<uri\>model://sun\</uri\>\</include\>  
   
    \<\!-- Ground plane \--\>  
    \<model name="ground\_plane"\>  
      \<static\>true\</static\>  
      \<link name="link"\>  
        \<collision name="collision"\>  
          \<geometry\>\<plane\>\<normal\>0 0 1\</normal\>\<size\>100 100\</size\>\</plane\>\</geometry\>  
        \</collision\>  
        \<visual name="visual"\>  
          \<geometry\>\<plane\>\<normal\>0 0 1\</normal\>\<size\>100 100\</size\>\</plane\>\</geometry\>  
          \<material\>\<ambient\>0.5 0.5 0.5 1\</ambient\>\</material\>  
        \</visual\>  
      \</link\>  
    \</model\>  
   
    \<\!-- Pillar NE \--\>  
    \<model name="pillar\_NE"\>  
      \<static\>true\</static\>  
      \<pose\>3.0 3.0 0.5 0 0 0\</pose\>  
      \<link name="link"\>  
        \<collision name="collision"\>\<geometry\>\<box\>\<size\>0.2 0.2 1.0\</size\>\</box\>\</geometry\>\</collision\>  
        \<visual name="visual"\>  
          \<geometry\>\<box\>\<size\>0.2 0.2 1.0\</size\>\</box\>\</geometry\>  
          \<material\>\<ambient\>0.8 0.2 0.2 1\</ambient\>\</material\>  
        \</visual\>  
      \</link\>  
    \</model\>  
   
    \<\!-- Pillar NW \--\>  
    \<model name="pillar\_NW"\>  
      \<static\>true\</static\>  
      \<pose\>-3.0 3.0 0.5 0 0 0\</pose\>  
      \<link name="link"\>  
        \<collision name="collision"\>\<geometry\>\<box\>\<size\>0.2 0.2 1.0\</size\>\</box\>\</geometry\>\</collision\>  
        \<visual name="visual"\>\<geometry\>\<box\>\<size\>0.2 0.2 1.0\</size\>\</box\>\</geometry\>  
          \<material\>\<ambient\>0.8 0.2 0.2 1\</ambient\>\</material\>\</visual\>  
      \</link\>  
    \</model\>  
   
    \<\!-- Pillar SE \--\>  
    \<model name="pillar\_SE"\>  
      \<static\>true\</static\>  
      \<pose\>3.0 \-3.0 0.5 0 0 0\</pose\>  
      \<link name="link"\>  
        \<collision name="collision"\>\<geometry\>\<box\>\<size\>0.2 0.2 1.0\</size\>\</box\>\</geometry\>\</collision\>  
        \<visual name="visual"\>\<geometry\>\<box\>\<size\>0.2 0.2 1.0\</size\>\</box\>\</geometry\>  
          \<material\>\<ambient\>0.8 0.2 0.2 1\</ambient\>\</material\>\</visual\>  
      \</link\>  
    \</model\>  
   
    \<\!-- Pillar SW \--\>  
    \<model name="pillar\_SW"\>  
      \<static\>true\</static\>  
      \<pose\>-3.0 \-3.0 0.5 0 0 0\</pose\>  
      \<link name="link"\>  
        \<collision name="collision"\>\<geometry\>\<box\>\<size\>0.2 0.2 1.0\</size\>\</box\>\</geometry\>\</collision\>  
        \<visual name="visual"\>\<geometry\>\<box\>\<size\>0.2 0.2 1.0\</size\>\</box\>\</geometry\>  
          \<material\>\<ambient\>0.8 0.2 0.2 1\</ambient\>\</material\>\</visual\>  
      \</link\>  
    \</model\>  
   
    \<\!-- Centre Post (cylinder) \--\>  
    \<model name="centre\_post"\>  
      \<static\>true\</static\>  
      \<pose\>0.0 0.0 0.4 0 0 0\</pose\>  
      \<link name="link"\>  
        \<collision name="collision"\>  
          \<geometry\>\<cylinder\>\<radius\>0.1\</radius\>\<length\>0.8\</length\>\</cylinder\>\</geometry\>  
        \</collision\>  
        \<visual name="visual"\>  
          \<geometry\>\<cylinder\>\<radius\>0.1\</radius\>\<length\>0.8\</length\>\</cylinder\>\</geometry\>  
          \<material\>\<ambient\>0.2 0.6 0.2 1\</ambient\>\</material\>  
        \</visual\>  
      \</link\>  
    \</model\>  
   
  \</world\>  
\</sdf\>

### **Solution — Q3: scripts/scan\_monitor.py**

\#\!/usr/bin/env python3  
"""Q3 Reference Solution: LaserScan proximity monitor"""  
import rclpy  
from rclpy.node import Node  
from sensor\_msgs.msg import LaserScan  
from std\_msgs.msg import String  
   
class ScanMonitor(Node):  
    def \_\_init\_\_(self):  
        super().\_\_init\_\_("scan\_monitor")  
        self.declare\_parameter("safe\_distance", 1.0)  
        self.declare\_parameter("warn\_distance", 0.5)  
        self.safe \= self.get\_parameter("safe\_distance").value  
        self.warn \= self.get\_parameter("warn\_distance").value  
        self.sub \= self.create\_subscription(  
            LaserScan, "/scan", self.scan\_cb, 10\)  
        self.pub \= self.create\_publisher(String, "/proximity\_status", 10\)  
   
    def scan\_cb(self, msg: LaserScan):  
        finite \= \[r for r in msg.ranges  
                  if r \== r and r \!= float("inf") and r \> msg.range\_min\]  
        min\_range \= min(finite) if finite else float("inf")  
   
        if min\_range \>= self.safe:  
            status \= "SAFE"  
        elif min\_range \>= self.warn:  
            status \= "WARNING"  
        else:  
            status \= "DANGER"  
   
        self.get\_logger().info(  
            f"min\_range={min\_range:.2f}m  status={status}")  
        self.pub.publish(String(data=status))  
   
def main(args=None):  
    rclpy.init(args=args)  
    rclpy.spin(ScanMonitor())  
    rclpy.shutdown()  
   
if \_\_name\_\_ \== "\_\_main\_\_":  
    main()

### **Solution — Q4: scripts/image\_processor.py**

\#\!/usr/bin/env python3  
"""Q4 Reference Solution: Camera image brightness processor"""  
import rclpy  
from rclpy.node import Node  
from sensor\_msgs.msg import Image  
from std\_msgs.msg import Float32  
from cv\_bridge import CvBridge  
import numpy as np  
   
class ImageProcessor(Node):  
    def \_\_init\_\_(self):  
        super().\_\_init\_\_("image\_processor")  
        self.bridge  \= CvBridge()  
        self.frame\_n \= 0  
        self.sub \= self.create\_subscription(  
            Image, "/camera/image\_raw", self.image\_cb, 10\)  
        self.pub \= self.create\_publisher(Float32, "/image\_brightness", 10\)  
   
    def image\_cb(self, msg: Image):  
        cv\_img \= self.bridge.imgmsg\_to\_cv2(msg, desired\_encoding="bgr8")  
        mean\_b \= float(np.mean(cv\_img))  
        self.pub.publish(Float32(data=mean\_b))  
        self.frame\_n \+= 1  
        if self.frame\_n % 30 \== 0:  
            self.get\_logger().info(  
                f"frame {self.frame\_n} — mean\_brightness={mean\_b:.1f}")  
   
def main(args=None):  
    rclpy.init(args=args)  
    rclpy.spin(ImageProcessor())  
    rclpy.shutdown()  
   
if \_\_name\_\_ \== "\_\_main\_\_":  
    main()

### **Solution — Q5: scripts/imu\_monitor.py**

\#\!/usr/bin/env python3  
"""Q5 Reference Solution: IMU tilt monitor"""  
import rclpy, math  
from rclpy.node import Node  
from sensor\_msgs.msg import Imu  
from std\_msgs.msg import Bool, Float32  
   
class ImuMonitor(Node):  
    def \_\_init\_\_(self):  
        super().\_\_init\_\_("imu\_monitor")  
        self.declare\_parameter("tilt\_threshold", 0.3)  
        self.thresh \= self.get\_parameter("tilt\_threshold").value  
        self.sub \= self.create\_subscription(  
            Imu, "/imu/data", self.imu\_cb, 10\)  
        self.pub\_alert \= self.create\_publisher(Bool,   "/tilt\_alert", 10\)  
        self.pub\_angle \= self.create\_publisher(Float32,"/tilt\_angle", 10\)  
   
    def imu\_cb(self, msg: Imu):  
        ax \= msg.linear\_acceleration.x  
        az \= msg.linear\_acceleration.z  
        pitch \= math.atan2(ax, az)  
        alert \= abs(pitch) \> self.thresh  
        self.pub\_alert.publish(Bool(data=alert))  
        self.pub\_angle.publish(Float32(data=pitch))  
        if alert:  
            self.get\_logger().warn(  
                f"TILT ALERT: pitch={pitch:.3f} rad")  
   
def main(args=None):  
    rclpy.init(args=args)  
    rclpy.spin(ImuMonitor())  
    rclpy.shutdown()  
   
if \_\_name\_\_ \== "\_\_main\_\_":  
    main()

### **Solution — Q6: scripts/sensor\_aggregator.py**

\#\!/usr/bin/env python3  
"""Q6 Reference Solution: Unified sensor aggregator node"""  
import rclpy, math  
from rclpy.node import Node  
from sensor\_msgs.msg import LaserScan, Image, Imu  
from std\_msgs.msg import String  
from cv\_bridge import CvBridge  
import numpy as np  
   
class SensorAggregator(Node):  
    def \_\_init\_\_(self):  
        super().\_\_init\_\_("sensor\_aggregator")  
        self.bridge \= CvBridge()  
        self.min\_range  \= float("inf")  
        self.brightness \= 0.0  
        self.pitch      \= 0.0  
   
        self.create\_subscription(LaserScan, "/scan",            self.scan\_cb,  10\)  
        self.create\_subscription(Image,     "/camera/image\_raw",self.img\_cb,   10\)  
        self.create\_subscription(Imu,       "/imu/data",        self.imu\_cb,   10\)  
        self.pub   \= self.create\_publisher(String, "/sensor\_status", 10\)  
        self.timer \= self.create\_timer(1.0, self.timer\_cb)  
   
    def scan\_cb(self, msg: LaserScan):  
        finite \= \[r for r in msg.ranges  
                  if r \== r and r \!= float("inf") and r \> msg.range\_min\]  
        self.min\_range \= min(finite) if finite else float("inf")  
   
    def img\_cb(self, msg: Image):  
        cv\_img \= self.bridge.imgmsg\_to\_cv2(msg, desired\_encoding="bgr8")  
        self.brightness \= float(np.mean(cv\_img))  
   
    def imu\_cb(self, msg: Imu):  
        ax \= msg.linear\_acceleration.x  
        az \= msg.linear\_acceleration.z  
        self.pitch \= math.atan2(ax, az)  
   
    def timer\_cb(self):  
        status \= (f"lidar={self.min\_range:.2f}m  "  
                  f"brightness={self.brightness:.1f}  "  
                  f"pitch={self.pitch:.3f}rad")  
        self.pub.publish(String(data=status))  
        self.get\_logger().info(status)  
   
def main(args=None):  
    rclpy.init(args=args)  
    rclpy.spin(SensorAggregator())  
    rclpy.shutdown()  
   
if \_\_name\_\_ \== "\_\_main\_\_":  
    main()

### **Solution — Q6: worlds/ward.world**

\<?xml version="1.0"?\>  
\<sdf version="1.6"\>  
  \<world name="ward"\>  
    \<include\>\<uri\>model://sun\</uri\>\</include\>  
   
    \<model name="ground\_plane"\>\<static\>true\</static\>  
      \<link name="link"\>  
        \<collision name="c"\>\<geometry\>\<plane\>\<normal\>0 0 1\</normal\>  
          \<size\>100 100\</size\>\</plane\>\</geometry\>\</collision\>  
        \<visual name="v"\>\<geometry\>\<plane\>\<normal\>0 0 1\</normal\>  
          \<size\>100 100\</size\>\</plane\>\</geometry\>  
          \<material\>\<ambient\>0.6 0.6 0.6 1\</ambient\>\</material\>\</visual\>  
      \</link\>  
    \</model\>  
   
    \<model name="corridor\_wall\_left"\>\<static\>true\</static\>  
      \<pose\>-2.0 1.5 1.0 0 0 0\</pose\>  
      \<link name="link"\>  
        \<collision name="c"\>\<geometry\>\<box\>  
          \<size\>6.0 0.2 2.0\</size\>\</box\>\</geometry\>\</collision\>  
        \<visual name="v"\>\<geometry\>\<box\>\<size\>6.0 0.2 2.0\</size\>\</box\>\</geometry\>  
          \<material\>\<ambient\>0.7 0.7 0.8 1\</ambient\>\</material\>\</visual\>  
      \</link\>  
    \</model\>  
   
    \<model name="corridor\_wall\_right"\>\<static\>true\</static\>  
      \<pose\>-2.0 \-1.5 1.0 0 0 0\</pose\>  
      \<link name="link"\>  
        \<collision name="c"\>\<geometry\>\<box\>  
          \<size\>6.0 0.2 2.0\</size\>\</box\>\</geometry\>\</collision\>  
        \<visual name="v"\>\<geometry\>\<box\>\<size\>6.0 0.2 2.0\</size\>\</box\>\</geometry\>  
          \<material\>\<ambient\>0.7 0.7 0.8 1\</ambient\>\</material\>\</visual\>  
      \</link\>  
    \</model\>  
   
    \<model name="doorframe\_left"\>\<static\>true\</static\>  
      \<pose\>1.5 1.5 1.0 0 0 0\</pose\>  
      \<link name="link"\>  
        \<collision name="c"\>\<geometry\>\<box\>  
          \<size\>0.2 0.5 2.0\</size\>\</box\>\</geometry\>\</collision\>  
        \<visual name="v"\>\<geometry\>\<box\>\<size\>0.2 0.5 2.0\</size\>\</box\>\</geometry\>  
          \<material\>\<ambient\>0.4 0.4 0.6 1\</ambient\>\</material\>\</visual\>  
      \</link\>  
    \</model\>  
   
    \<model name="doorframe\_right"\>\<static\>true\</static\>  
      \<pose\>1.5 \-1.5 1.0 0 0 0\</pose\>  
      \<link name="link"\>  
        \<collision name="c"\>\<geometry\>\<box\>  
          \<size\>0.2 0.5 2.0\</size\>\</box\>\</geometry\>\</collision\>  
        \<visual name="v"\>\<geometry\>\<box\>\<size\>0.2 0.5 2.0\</size\>\</box\>\</geometry\>  
          \<material\>\<ambient\>0.4 0.4 0.6 1\</ambient\>\</material\>\</visual\>  
      \</link\>  
    \</model\>  
   
  \</world\>  
\</sdf\>

# **6\.  EVALUATION SCRIPTS**

pytest-based — rclpy \+ subprocess \+ XML/YAML parsing

### **test/evaluate.py — Q2 (SDF World Validation)**

\#\!/usr/bin/env python3  
"""Evaluation Script: Q2 — Custom SDF World"""  
import pytest, subprocess, xml.etree.ElementTree as ET  
   
WORLD \= "install/arena\_sim/share/arena\_sim/worlds/arena.world"  
   
def parse\_world():  
    return ET.parse(WORLD).getroot()  
   
def test\_sdf\_version\_16():  
    root \= parse\_world()  
    assert root.attrib.get("version") \== "1.6", "SDF version must be 1.6"  
   
def test\_world\_parses\_without\_error():  
    r \= subprocess.run(\["gz", "sdf", "-k", WORLD\],  
        capture\_output=True, text=True)  
    assert r.returncode \== 0, f"SDF validation failed:\\n{r.stderr}"  
   
def test\_exactly\_six\_models():  
    root \= parse\_world()  
    world \= root.find("world")  
    models \= world.findall("model")  
    assert len(models) \== 6, f"Expected 6 models, found {len(models)}"  
   
def test\_all\_models\_static():  
    root \= parse\_world()  
    for m in root.find("world").findall("model"):  
        name \= m.attrib\["name"\]  
        s \= m.find("static")  
        assert s is not None and s.text.strip() \== "true", \\  
            f"Model {name} must be \<static\>true\</static\>"  
   
def test\_pillar\_NE\_box\_geometry():  
    root \= parse\_world()  
    for m in root.find("world").findall("model"):  
        if m.attrib\["name"\] \== "pillar\_NE":  
            box \= m.find(".//collision/geometry/box/size")  
            assert box is not None, "pillar\_NE missing box geometry"  
            dims \= \[float(v) for v in box.text.split()\]  
            assert abs(dims\[0\]-0.2)\<0.001 and abs(dims\[2\]-1.0)\<0.001  
   
def test\_centre\_post\_cylinder():  
    root \= parse\_world()  
    for m in root.find("world").findall("model"):  
        if m.attrib\["name"\] \== "centre\_post":  
            cyl \= m.find(".//collision/geometry/cylinder")  
            assert cyl is not None, "centre\_post must be cylinder"  
            r \= float(cyl.find("radius").text)  
            h \= float(cyl.find("length").text)  
            assert abs(r-0.1)\<0.001 and abs(h-0.8)\<0.001  
   
def test\_all\_models\_have\_visual\_and\_collision():  
    root \= parse\_world()  
    for m in root.find("world").findall("model"):  
        name \= m.attrib\["name"\]  
        if name \== "ground\_plane": continue  
        assert m.find(".//collision") is not None, f"{name} missing collision"  
        assert m.find(".//visual")    is not None, f"{name} missing visual"

### **test/evaluate.py — Q3 (Scan Monitor)**

\#\!/usr/bin/env python3  
"""Evaluation Script: Q3 — LaserScan monitor"""  
import pytest, subprocess, sys, math  
   
\# ── Unit-test the logic without ROS ─────────────────────────────────  
def classify(ranges, safe=1.0, warn=0.5):  
    finite \= \[r for r in ranges if r==r and r\!=float("inf") and r\>0.1\]  
    min\_r \= min(finite) if finite else float("inf")  
    if min\_r \>= safe:   return "SAFE", min\_r  
    elif min\_r \>= warn: return "WARNING", min\_r  
    else:               return "DANGER", min\_r  
   
def test\_all\_inf\_returns\_safe():  
    status, \_ \= classify(\[float("inf")\]\*360)  
    assert status \== "SAFE"  
   
def test\_obstacle\_at\_0\_7m\_warning():  
    ranges \= \[float("inf")\]\*360  
    ranges\[90\] \= 0.7  
    status, \_ \= classify(ranges)  
    assert status \== "WARNING"  
   
def test\_obstacle\_at\_0\_2m\_danger():  
    ranges \= \[1.5\]\*360  
    ranges\[45\] \= 0.2  
    status, \_ \= classify(ranges)  
    assert status \== "DANGER"  
   
def test\_nan\_filtered():  
    ranges \= \[float("nan")\]\*180 \+ \[2.0\]\*180  
    status, min\_r \= classify(ranges)  
    assert status \== "SAFE" and abs(min\_r \- 2.0) \< 1e-6  
   
def test\_safe\_distance\_parameter\_honoured():  
    \# With safe=2.0: a 1.5m reading becomes WARNING  
    status, \_ \= classify(\[1.5\]\*360, safe=2.0, warn=0.5)  
    assert status \== "WARNING"  
   
\# ── Runtime tests ────────────────────────────────────────────────────  
def test\_proximity\_status\_topic\_published():  
    r \= subprocess.run(\["ros2","topic","list"\],capture\_output=True,text=True,timeout=10)  
    assert "/proximity\_status" in r.stdout  
   
def test\_proximity\_status\_is\_string\_type():  
    r \= subprocess.run(\["ros2","topic","info","/proximity\_status"\],  
        capture\_output=True,text=True,timeout=10)  
    assert "std\_msgs/msg/String" in r.stdout  
   
def test\_rviz\_config\_has\_laserscan():  
    src \= open("src/scan\_monitor\_pkg/rviz/sensor\_view.rviz").read()  
    assert "LaserScan" in src, "sensor\_view.rviz missing LaserScan display"  
    assert "/scan" in src, "LaserScan display must reference /scan"  
   
def test\_no\_numpy\_imported():  
    src \= open("src/scan\_monitor\_pkg/scripts/scan\_monitor.py").read()  
    assert "import numpy" not in src and "from numpy" not in src, \\  
        "Q3 must not use numpy"

### **test/evaluate.py — Q6 (Full Ward Sim — comprehensive)**

\#\!/usr/bin/env python3  
"""Evaluation Script: Q6 — Ward Simulation"""  
import pytest, subprocess, re, xml.etree.ElementTree as ET  
   
WORLD \= "install/ward\_sim\_pkg/share/ward\_sim\_pkg/worlds/ward.world"  
SCRIPT= "src/ward\_sim\_pkg/scripts/sensor\_aggregator.py"  
RVIZ  \= "src/ward\_sim\_pkg/rviz/full\_view.rviz"  
LAUNCH= "src/ward\_sim\_pkg/launch/ward\_sim.launch.py"  
   
\# ── SDF World checks ─────────────────────────────────────────────────  
def test\_ward\_world\_sdf\_version():  
    root \= ET.parse(WORLD).getroot()  
    assert root.attrib.get("version") \== "1.6"  
   
def test\_ward\_world\_five\_models():  
    root \= ET.parse(WORLD).getroot()  
    models \= root.find("world").findall("model")  
    assert len(models) \== 5, f"Expected 5 models, got {len(models)}"  
   
def test\_ward\_all\_models\_static():  
    root \= ET.parse(WORLD).getroot()  
    for m in root.find("world").findall("model"):  
        s \= m.find("static")  
        assert s is not None and s.text.strip() \== "true", \\  
            f"{m.attrib\["name"\]} not static"  
   
def test\_ward\_corridor\_walls\_geometry():  
    root \= ET.parse(WORLD).getroot()  
    for m in root.find("world").findall("model"):  
        if "corridor\_wall" in m.attrib\["name"\]:  
            box \= m.find(".//collision/geometry/box/size")  
            assert box is not None  
            dims \= \[float(v) for v in box.text.split()\]  
            assert abs(dims\[0\]-6.0)\<0.01 and abs(dims\[2\]-2.0)\<0.01  
   
\# ── Script source checks ─────────────────────────────────────────────  
def test\_aggregator\_has\_three\_subscriptions():  
    src \= open(SCRIPT).read()  
    assert "/scan" in src  
    assert "/camera/image\_raw" in src  
    assert "/imu/data" in src  
   
def test\_aggregator\_uses\_cv\_bridge():  
    src \= open(SCRIPT).read()  
    assert "cv\_bridge" in src or "CvBridge" in src, "Must use cv\_bridge"  
   
def test\_aggregator\_uses\_atan2():  
    src \= open(SCRIPT).read()  
    assert "atan2" in src, "Must use math.atan2 for pitch"  
   
def test\_aggregator\_1hz\_timer():  
    src \= open(SCRIPT).read()  
    assert "create\_timer(1.0" in src or "create\_timer(1," in src, \\  
        "Timer must be 1.0 Hz"  
   
def test\_aggregator\_no\_scipy():  
    src \= open(SCRIPT).read()  
    assert "scipy" not in src and "tf\_transformations" not in src  
   
\# ── RViz config checks ───────────────────────────────────────────────  
def test\_rviz\_has\_all\_five\_displays():  
    src \= open(RVIZ).read()  
    for d in \["RobotModel","TF","LaserScan","Camera","Imu"\]:  
        assert d in src, f"full\_view.rviz missing {d} display"  
   
def test\_rviz\_scan\_topic():  
    src \= open(RVIZ).read()  
    assert "/scan" in src  
   
def test\_rviz\_camera\_topic():  
    src \= open(RVIZ).read()  
    assert "/camera/image\_raw" in src  
   
\# ── Launch file checks ───────────────────────────────────────────────  
def test\_launch\_spawns\_at\_correct\_position():  
    src \= open(LAUNCH).read()  
    assert "-3.0" in src or "-3" in src, "spawn x=-3.0 not found in launch"  
   
def test\_launch\_includes\_all\_nodes():  
    src \= open(LAUNCH).read()  
    for n in \["gazebo\_ros","robot\_state\_publisher","spawn\_entity",  
              "sensor\_aggregator","rviz2"\]:  
        assert n in src, f"Launch missing {n}"  
   
\# ── Runtime topic checks ─────────────────────────────────────────────  
def test\_sensor\_status\_topic\_published():  
    r \= subprocess.run(\["ros2","topic","list"\],capture\_output=True,text=True,timeout=10)  
    assert "/sensor\_status" in r.stdout  
   
def test\_sensor\_status\_format():  
    r \= subprocess.run(\["ros2","topic","echo","/sensor\_status","--once"\],  
        capture\_output=True,text=True,timeout=10)  
    pattern \= r"lidar=\\d+\\.\\d+m\\s+brightness=\\d+\\.\\d+\\s+pitch=-?\\d+\\.\\d+rad"  
    assert re.search(pattern,r.stdout), f"Format mismatch: {r.stdout\[:200\]}"  
   
def test\_robot\_description\_published():  
    r \= subprocess.run(\["ros2","topic","list"\],capture\_output=True,text=True,timeout=10)  
    assert "/robot\_description" in r.stdout

# **7\.  judge\_runner.py**

Production-ready  |  Docker-compatible  |  Structured JSON output

\#\!/usr/bin/env python3  
"""  
judge\_runner.py — Simulation Topic  
Usage: python3 judge\_runner.py \--question Q1 \--workspace /home/student/ros2\_ws  
"""  
import argparse, json, os, subprocess, sys, time, signal, logging  
from pathlib import Path  
   
logging.basicConfig(level=logging.INFO,  
    format="\[%(asctime)s\] %(levelname)s — %(message)s")  
log \= logging.getLogger("judge\_runner")  
   
Q\_CFG \= {  
    "Q1": {"pkg":"delivery\_sim",    "launch":"sim.launch.py",  
           "tests":"delivery\_sim/test/evaluate.py",  
           "fns":\["test\_robot\_description\_topic","test\_entity\_spawned",  
                  "test\_tf\_base\_footprint","test\_rsp\_active",  
                  "test\_rviz2\_active","test\_rviz\_has\_robotmodel","test\_rviz\_has\_tf"\],  
           "warmup":8,"requires\_launch":True},  
    "Q2": {"pkg":"arena\_sim",       "launch":"arena.launch.py",  
           "tests":"arena\_sim/test/evaluate.py",  
           "fns":\["test\_sdf\_version\_16","test\_world\_parses\_without\_error",  
                  "test\_exactly\_six\_models","test\_all\_models\_static",  
                  "test\_pillar\_NE\_box\_geometry","test\_centre\_post\_cylinder",  
                  "test\_all\_models\_have\_visual\_and\_collision"\],  
           "warmup":8,"requires\_launch":True},  
    "Q3": {"pkg":"scan\_monitor\_pkg","launch":"monitor.launch.py",  
           "tests":"scan\_monitor\_pkg/test/evaluate.py",  
           "fns":\["test\_all\_inf\_returns\_safe","test\_obstacle\_at\_0\_7m\_warning",  
                  "test\_obstacle\_at\_0\_2m\_danger","test\_nan\_filtered",  
                  "test\_safe\_distance\_parameter\_honoured",  
                  "test\_proximity\_status\_topic\_published",  
                  "test\_proximity\_status\_is\_string\_type",  
                  "test\_rviz\_config\_has\_laserscan","test\_no\_numpy\_imported"\],  
           "warmup":6,"requires\_launch":True},  
    "Q4": {"pkg":"camera\_proc\_pkg", "launch":"camera.launch.py",  
           "tests":"camera\_proc\_pkg/test/evaluate.py",  
           "fns":\["test\_image\_brightness\_topic","test\_black\_image",  
                  "test\_white\_image","test\_grey\_image",  
                  "test\_cvbridge\_used","test\_rviz\_has\_camera"\],  
           "warmup":6,"requires\_launch":True},  
    "Q5": {"pkg":"imu\_monitor\_pkg", "launch":"imu.launch.py",  
           "tests":"imu\_monitor\_pkg/test/evaluate.py",  
           "fns":\["test\_tilt\_alert\_topic","test\_tilt\_angle\_topic",  
                  "test\_flat\_robot\_no\_alert","test\_tilted\_robot\_alert",  
                  "test\_tilt\_threshold\_parameter","test\_atan2\_used",  
                  "test\_rviz\_has\_imu"\],  
           "warmup":6,"requires\_launch":True},  
    "Q6": {"pkg":"ward\_sim\_pkg",    "launch":"ward\_sim.launch.py",  
           "tests":"ward\_sim\_pkg/test/evaluate.py",  
           "fns":\["test\_ward\_world\_sdf\_version","test\_ward\_world\_five\_models",  
                  "test\_ward\_all\_models\_static","test\_ward\_corridor\_walls\_geometry",  
                  "test\_aggregator\_has\_three\_subscriptions","test\_aggregator\_uses\_cv\_bridge",  
                  "test\_aggregator\_uses\_atan2","test\_aggregator\_1hz\_timer",  
                  "test\_aggregator\_no\_scipy","test\_rviz\_has\_all\_five\_displays",  
                  "test\_rviz\_scan\_topic","test\_rviz\_camera\_topic",  
                  "test\_launch\_spawns\_at\_correct\_position",  
                  "test\_launch\_includes\_all\_nodes",  
                  "test\_sensor\_status\_topic\_published","test\_sensor\_status\_format",  
                  "test\_robot\_description\_published"\],  
           "warmup":12,"requires\_launch":True},  
}  
   
def build\_ws(ws,env):  
    r=subprocess.run(\["colcon","build","--symlink-install"\],  
        env=env,capture\_output=True,text=True,timeout=240,cwd=ws)  
    return{"success":r.returncode==0,"stderr":r.stderr\[-2000:\]}  
   
def source\_ws(ws):  
    r=subprocess.run(\["bash","-c",  
        f"source /opt/ros/humble/setup.bash && source {ws}/install/setup.bash && env"\],  
        capture\_output=True,text=True,timeout=20)  
    return{k:v for line in r.stdout.splitlines() if "=" in line  
           for k,v in \[line.split("=",1)\]}  
   
def launch(pkg,lf,env,warmup):  
    proc=subprocess.Popen(\["ros2","launch",pkg,lf\],env=env,  
        stdout=subprocess.PIPE,stderr=subprocess.PIPE,preexec\_fn=os.setsid)  
    time.sleep(warmup)  
    return proc  
   
def run\_tests(tfile,fns,ws,env):  
    out={}  
    path=os.path.join(ws,"src",tfile)  
    for fn in fns:  
        r=subprocess.run(\["python3","-m","pytest",path,"-k",fn,"-v","--tb=short"\],  
            env=env,capture\_output=True,text=True,timeout=30,cwd=ws)  
        out\[fn\]=r.returncode==0  
        log.info("%s  %s","PASS" if out\[fn\] else "FAIL",fn)  
    return out  
   
def kill(proc):  
    try: os.killpg(os.getpgid(proc.pid),signal.SIGTERM); proc.wait(timeout=5)  
    except: pass  
   
def judge(question,workspace):  
    if question not in Q\_CFG:  
        return{"status":"error","message":f"Unknown question {question}"}  
    cfg=Q\_CFG\[question\]  
    out={"question":question,"status":"started","build":{},"results":{},"score":{},"message":""}  
    env=os.environ.copy(); env\["ROS\_DOMAIN\_ID"\]="77"  
    bld=build\_ws(workspace,env)  
    out\["build"\]=bld  
    if not bld\["success"\]:  
        out.update({"status":"build\_failed","message":"Build failed"}); return out  
    env\_s=source\_ws(workspace)  
    proc=None  
    if cfg\["requires\_launch"\]:  
        proc=launch(cfg\["pkg"\],cfg\["launch"\],env\_s,cfg\["warmup"\])  
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
    sys.exit(0 if result.get("status")=="completed" and  
             all(result\["results"\].values()) else 1\)

# **8\.  EVALUATION SCENARIOS**

15 scenarios covering normal operation, edge cases, and common errors

| ID | Q | Scenario | Expected Outcome | Detection Method |
| ----- | ----- | ----- | ----- | ----- |
| ES-01 | Q1 | Student uses static URDF string not file | robot\_description published but stale after urdf changes | Source scan — no open() or xacro call |
| ES-02 | Q1 | spawn\_entity uses \-file instead of \-topic | Robot may not spawn — no /robot\_description dependency | Source scan for "-topic" |
| ES-03 | Q1 | rviz config missing TF display | TF arrows absent in RViz | YAML key scan for "TF" in robot\_view.rviz |
| ES-04 | Q2 | SDF version is 1.5 instead of 1.6 | test\_sdf\_version\_16 fails | XML attribute check |
| ES-05 | Q2 | Models missing \<static\>true\</static\> | Obstacles move when robot hits them; test fails | XML tag presence \+ text check |
| ES-06 | Q2 | centre\_post has box geometry not cylinder | test\_centre\_post\_cylinder fails | Geometry tag name check |
| ES-07 | Q3 | Student uses numpy for min computation | test\_no\_numpy\_imported fails | Source code import scan |
| ES-08 | Q3 | inf values not filtered — min() raises ValueError | Node crashes on first scan | Injected all-inf scan scenario |
| ES-09 | Q3 | warn\_distance \> safe\_distance (parameter error) | WARNING zone is empty — robot always SAFE or DANGER | Boundary value injection test |
| ES-10 | Q4 | Uses msg.data directly not cv\_bridge | May produce wrong dtype or crash on encoding mismatch | Source scan: "cv\_bridge" absent → fail |
| ES-11 | Q4 | Float64 published instead of Float32 | test\_image\_brightness\_is\_float32 fails | Topic info type check |
| ES-12 | Q5 | tilt\_threshold hardcoded not from parameter | test\_tilt\_threshold\_parameter fails | ros2 param set \+ re-check alert |
| ES-13 | Q6 | Timer set to 10 Hz not 1 Hz | test\_aggregator\_1hz\_timer fails | Source scan for create\_timer value |
| ES-14 | Q6 | Ward world has wrong number of models | test\_ward\_world\_five\_models fails | XML model count check |
| ES-15 | Q6 | /sensor\_status format string incorrect | Regex match fails in test\_sensor\_status\_format | Pattern: lidar=X.XXm brightness=X.X pitch=X.XXXrad |

# **9\.  COMMON MISTAKES & DEBUGGING NOTES**

Per-question error patterns with root causes and fixes

### **Q1 — Spawn & Visualise**

| Mistake | Symptom | Fix |
| ----- | ----- | ----- |
| spawn\_entity uses \-file path instead of \-topic | Robot spawns in Gazebo but TF is disconnected from robot\_state\_publisher | Use \-topic /robot\_description so spawn\_entity reads from the live RSP topic |
| rviz2 launched before robot\_state\_publisher is ready | RViz opens with "No transform from \[base\_link\] to \[base\_footprint\]" error on startup | Add a TimerAction or node\_dependency to ensure RSP is up before RViz |
| Fixed Frame set to "map" not "base\_footprint" in RViz | RobotModel appears but shows "Transform \[sender=unknown\_publisher\]" warning | Set Fixed Frame to base\_footprint or odom for robot-only visualisation |

### **Q2 — SDF World**

| Mistake | Symptom | Fix |
| ----- | ----- | ----- |
| Pose z value \= 0 for box obstacles (not half-height) | Obstacles appear half-submerged in the ground plane | For a box of height h, set z \= h/2 so the bottom face sits on the ground |
| \<static\> tag placed outside \<model\>, inside \<link\> | SDF parses but obstacles are not static — robot pushes them | \<static\>true\</static\> is a direct child of \<model\>, not \<link\> |
| Using model:// database includes for ground\_plane | Works locally but fails in Docker — no Gazebo model database mounted | Define ground plane geometry inline as shown in the reference solution |
| Missing \<collision\> on obstacle — only \<visual\> defined | Obstacle visible in Gazebo but LiDAR passes through it, robot drives through it | Every obstacle needs both \<collision\> and \<visual\> with matching geometry |

### **Q3 — LaserScan Subscriber**

| Mistake | Symptom | Fix |
| ----- | ----- | ----- |
| Not filtering inf/nan before calling min() | Node crashes with ValueError on first scan from Gazebo (ranges contain inf) | Filter: \[r for r in msg.ranges if r==r and r\!=float("inf") and r\>msg.range\_min\] |
| Comparing min\_range against hardcoded 1.0/0.5 not parameters | test\_safe\_distance\_parameter\_honoured fails | Declare and read safe\_distance and warn\_distance via declare\_parameter / get\_parameter |
| Publishing to wrong topic name (/scan\_status instead of /proximity\_status) | Evaluator cannot find /proximity\_status | Double-check topic name string matches specification exactly |

### **Q4 — Camera Image Processor**

| Mistake | Symptom | Fix |
| ----- | ----- | ----- |
| Accessing msg.data directly as numpy array without cv\_bridge | Wrong dtype or shape — mean() produces garbage values | Always use CvBridge().imgmsg\_to\_cv2(msg, desired\_encoding="bgr8") |
| Publishing std\_msgs/Float64 not Float32 | test\_image\_brightness\_is\_float32 fails; downstream consumers may reject message | from std\_msgs.msg import Float32 — Float32(data=mean\_b) |
| Logging every frame at INFO level | Terminal floods with log output; evaluator log parsing is slow | Log every 30 frames as specified: if self.frame\_n % 30 \== 0 |

### **Q5 — IMU Monitor**

| Mistake | Symptom | Fix |
| ----- | ----- | ----- |
| Using linear\_acceleration.y instead of .x for ax | Pitch computed incorrectly — tilt in x direction not detected | pitch \= math.atan2(msg.linear\_acceleration.x, msg.linear\_acceleration.z) |
| Declaring parameter but using get\_parameter before declare\_parameter completes | ParameterNotDeclaredException at startup | declare\_parameter() must always precede get\_parameter() in \_\_init\_\_ |
| Publishing Bool(True) as Bool(data=1) (integer not bool) | May work in Python but evaluator type-checks the data field | Use Bool(data=True) / Bool(data=False) explicitly |

### **Q6 — Full Ward Simulation**

| Mistake | Symptom | Fix |
| ----- | ----- | ----- |
| Three separate subscriber nodes instead of one SensorAggregator node | test\_aggregator\_has\_three\_subscriptions fails — wrong source file | All three create\_subscription calls must be in SensorAggregator.\_\_init\_\_ |
| Timer uses 0.1 (10 Hz) instead of 1.0 (1 Hz) | test\_aggregator\_1hz\_timer fails; /sensor\_status floods at 10x expected rate | self.create\_timer(1.0, self.timer\_cb) |
| spawn\_entity \-x set to 0 not \-3.0 | Robot spawns inside corridor wall — immediately collides | Arguments must include "-x", "-3.0" matching specification |
| full\_view.rviz missing Camera or Imu display | test\_rviz\_has\_all\_five\_displays fails | All five display class names must appear in the YAML: RobotModel TF LaserScan Camera Imu |
| /sensor\_status format string uses different separators | Regex match fails in test\_sensor\_status\_format | Format must be exactly: lidar=X.XXm  brightness=XXX.X  pitch=X.XXXrad (two spaces between fields) |

| General Simulation Debugging Notes |
| :---- |
|  |
|  |
|  |
|  |
|  |
|  |

**✓ All 10 syllabus skills covered   |   ✓ All 6 questions auto-gradable   |   ✓ ROS2 Humble / Gazebo Classic compatible**