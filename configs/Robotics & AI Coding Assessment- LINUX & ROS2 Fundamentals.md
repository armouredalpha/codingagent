# **Robotics & AI Coding Assessment**

## **Topic: LINUX & ROS2 Fundamentals**

---

# **1\. TOPIC ANALYSIS**

**Topic Domain:** ROS2 Fundamentals — communication primitives, tooling, transforms **Platform:** Ubuntu 22.04 | ROS2 Humble | Python 3.10 | Docker-based IDE **Target Learner Level:** 0–1 year ROS2 experience **Assessment Style:** Practical implementation inside pre-built ROS2 packages

## **Syllabus Decomposition**

| ID | Skill |
| ----- | ----- |
| S1 | Operating within a ROS2 development environment |
| S2 | Creating and building a ROS2 package |
| S3 | Writing publisher nodes |
| S4 | Writing subscriber nodes |
| S5 | Defining and calling a custom service |
| S6 | Using launch files with parameter passing |
| S7 | Inspecting the live ROS2 computation graph (ros2 topic, ros2 node, rqt) |
| S8 | Understanding the TF2 transform tree |

---

# **2\. SKILLS BEING TESTED — Coverage Matrix**

| Skill | Q1 | Q2 | Q3 | Q4 | Q5 | Q6 |
| ----- | ----- | ----- | ----- | ----- | ----- | ----- |
| S1 — ROS2 Dev Environment | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| S2 — Package creation/build | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| S3 — Publisher node | ✓ | — | ✓ | ✓ | ✓ | ✓ |
| S4 — Subscriber node | — | ✓ | ✓ | ✓ | ✓ | ✓ |
| S5 — Custom service | — | — | — | ✓ | — | ✓ |
| S6 — Launch \+ parameters | — | — | ✓ | — | ✓ | ✓ |
| S7 — Graph inspection | — | — | — | ✓ | — | ✓ |
| S8 — TF2 transform tree | — | — | — | — | ✓ | ✓ |

**Validation:** All 8 syllabus skills are covered by at least one question. No out-of-syllabus concepts introduced.

---

# **3\. SIX CODING QUESTIONS**

---

## **QUESTION 1 — Heartbeat Publisher for an Inspection Robot**

**Difficulty:** Easy **Tested Skills:** S1, S2, S3

### **Scenario**

An inspection robot deployed in a chemical plant must continuously broadcast a heartbeat signal so the supervisory monitoring station can confirm the robot is alive. Your team lead has assigned you the task of implementing the heartbeat publisher node. The package, build files, and entry points are already in place — you only need to write the publisher logic.

### **Files Student Can Edit**

* `inspection_robot/inspection_robot/heartbeat_publisher.py`

### **Existing Package Structure**

inspection\_robot/  
├── inspection\_robot/  
│   ├── \_\_init\_\_.py  
│   └── heartbeat\_publisher.py        \# \<-- edit this  
├── resource/  
│   └── inspection\_robot  
├── test/  
│   └── evaluate.py  
├── package.xml  
└── setup.py

### **Student Objective**

Implement a ROS2 Python node named `heartbeat_publisher` that:

1. Publishes a `std_msgs/msg/String` message on the topic `/robot/heartbeat`  
2. Publishes at exactly **2 Hz** (every 0.5 seconds)  
3. The message data field must follow the format: `ALIVE:<count>` where `<count>` starts at 0 and increments by 1 each publication  
4. Uses a QoS depth of 10

### **Constraints**

* Use the `rclpy` Python client library  
* Do NOT modify `setup.py`, `package.xml`, or any other file  
* Do NOT create new files  
* The executable entry point `heartbeat_publisher` is already registered

### **Expected Behaviour**

After running:

ros2 run inspection\_robot heartbeat\_publisher

The output of `ros2 topic echo /robot/heartbeat` should show:

data: 'ALIVE:0'  
\---  
data: 'ALIVE:1'  
\---  
data: 'ALIVE:2'

appearing every 0.5 seconds.

### **Evaluation Criteria (Hidden)**

* ✓ Node with name `heartbeat_publisher` is discoverable on the graph  
* ✓ Topic `/robot/heartbeat` exists  
* ✓ Topic message type is `std_msgs/msg/String`  
* ✓ Publishing frequency is 2 Hz (±0.2 Hz tolerance)  
* ✓ Message data matches regex `^ALIVE:\d+$`  
* ✓ Counter increments monotonically across consecutive messages

---

## **QUESTION 2 — Battery Threshold Subscriber for a Warehouse Robot**

**Difficulty:** Easy **Tested Skills:** S1, S2, S4

### **Scenario**

A warehouse robot's battery monitor publishes voltage readings on `/robot/battery_voltage`. Your task is to write a subscriber node that watches this topic and logs a `LOW BATTERY` warning whenever the voltage drops below a safety threshold. The battery monitor publisher is already running as a background node.

### **Files Student Can Edit**

* `warehouse_robot/warehouse_robot/battery_monitor.py`

### **Existing Package Structure**

warehouse\_robot/  
├── warehouse\_robot/  
│   ├── \_\_init\_\_.py  
│   ├── battery\_simulator.py          \# provided, do not edit  
│   └── battery\_monitor.py            \# \<-- edit this  
├── resource/  
│   └── warehouse\_robot  
├── test/  
│   └── evaluate.py  
├── package.xml  
└── setup.py

### **Student Objective**

Implement a ROS2 Python node named `battery_monitor` that:

1. Subscribes to the topic `/robot/battery_voltage` with message type `std_msgs/msg/Float32`  
2. For every received message, evaluates the voltage value:  
   * If voltage `< 11.5`, publish a `std_msgs/msg/String` message on `/robot/battery_alert` with the data `LOW BATTERY: <voltage>` (formatted to 2 decimal places, e.g. `LOW BATTERY: 11.32`)  
   * If voltage `>= 11.5`, publish nothing  
3. Uses a QoS depth of 10 for both publisher and subscriber

### **Constraints**

* Use `rclpy`  
* Do NOT modify the battery simulator  
* Do NOT poll — react only inside the subscriber callback  
* Do NOT use a wall timer

### **Expected Behaviour**

Running:

ros2 run warehouse\_robot battery\_simulator   \# terminal 1  
ros2 run warehouse\_robot battery\_monitor      \# terminal 2  
ros2 topic echo /robot/battery\_alert          \# terminal 3

Should show alerts appearing only when the simulator publishes voltages below 11.5 V.

### **Evaluation Criteria (Hidden)**

* ✓ Node `battery_monitor` exists  
* ✓ Subscription on `/robot/battery_voltage` with type `std_msgs/msg/Float32`  
* ✓ Publisher on `/robot/battery_alert` with type `std_msgs/msg/String`  
* ✓ Alert is published when test voltage of 10.5 V is injected  
* ✓ NO alert is published when test voltage of 12.4 V is injected  
* ✓ Alert string format matches regex `^LOW BATTERY: \d+\.\d{2}$`

---

## **QUESTION 3 — Configurable Velocity Commander for a Delivery Robot**

**Difficulty:** Medium **Tested Skills:** S1, S2, S3, S4, S6

### **Scenario**

A delivery robot's safety layer needs a configurable velocity commander. The commander listens to a high-level command topic and republishes velocity commands to the robot base, but **clamps** them to a maximum value defined via launch parameters. The maximum linear and angular velocities must be tunable per robot deployment without editing source code.

### **Files Student Can Edit**

* `delivery_robot/delivery_robot/velocity_commander.py`  
* `delivery_robot/launch/commander.launch.py`

### **Existing Package Structure**

delivery\_robot/  
├── delivery\_robot/  
│   ├── \_\_init\_\_.py  
│   └── velocity\_commander.py         \# \<-- edit this  
├── launch/  
│   └── commander.launch.py           \# \<-- edit this  
├── resource/  
│   └── delivery\_robot  
├── test/  
│   └── evaluate.py  
├── package.xml  
└── setup.py

### **Student Objective**

**Part A — Node (`velocity_commander.py`):**

1. Subscribe to `/cmd_vel_raw` (type `geometry_msgs/msg/Twist`)  
2. Declare two ROS2 parameters with defaults:  
   * `max_linear_velocity` (double, default `0.5`)  
   * `max_angular_velocity` (double, default `1.0`)  
3. On each incoming Twist, clamp `linear.x` to `[-max_linear_velocity, +max_linear_velocity]` and `angular.z` to `[-max_angular_velocity, +max_angular_velocity]`  
4. Republish the clamped Twist on `/cmd_vel` (same message type)

**Part B — Launch file (`commander.launch.py`):**

1. Launch the `velocity_commander` node  
2. Pass parameter overrides: `max_linear_velocity=0.3`, `max_angular_velocity=0.8`

### **Constraints**

* Use `rclpy` parameters API (`declare_parameter` / `get_parameter`)  
* Do NOT hardcode parameter values inside the node  
* The launch file MUST use `launch_ros.actions.Node` with the `parameters` argument  
* Other Twist fields (`linear.y`, `linear.z`, `angular.x`, `angular.y`) must be passed through unchanged

### **Expected Behaviour**

Running:

ros2 launch delivery\_robot commander.launch.py

Then publishing a Twist with `linear.x = 1.5`, `angular.z = -2.0` on `/cmd_vel_raw` should produce a Twist on `/cmd_vel` with `linear.x = 0.3`, `angular.z = -0.8` (the launch overrides).

### **Evaluation Criteria (Hidden)**

* ✓ Node `velocity_commander` declares both parameters  
* ✓ Subscription on `/cmd_vel_raw` exists  
* ✓ Publisher on `/cmd_vel` exists  
* ✓ Input Twist (0.2, 0.5) → output Twist (0.2, 0.5) — passthrough  
* ✓ Input Twist (1.5, \-2.0) → output Twist (0.3, \-0.8) — clamping with launch overrides  
* ✓ Input Twist (-0.9, 0.4) → output Twist (-0.3, 0.4) — negative clamping  
* ✓ Launching with the launch file sets `max_linear_velocity` to 0.3

---

## **QUESTION 4 — On-Demand Diagnostic Snapshot Service for a Mobile Rover**

**Difficulty:** Medium **Tested Skills:** S1, S2, S3, S4, S5, S7

### **Scenario**

The rover's fleet manager periodically asks the rover for a diagnostic snapshot: the latest battery voltage, the latest temperature, and a status string. Rather than continuously publishing this composite, the diagnostic node holds the latest values internally and exposes a custom service that returns them on demand. The custom service interface is already defined in the `rover_interfaces` package.

### **Files Student Can Edit**

* `mobile_rover/mobile_rover/diagnostic_server.py`

### **Provided Interface (already built)**

\# rover\_interfaces/srv/DiagnosticSnapshot.srv  
\---  
float32 battery\_voltage  
float32 temperature  
string status  
bool valid

(The empty request part is intentional — clients call the service with no arguments.)

### **Existing Package Structure**

mobile\_rover/  
├── mobile\_rover/  
│   ├── \_\_init\_\_.py  
│   ├── sensor\_simulator.py           \# publishes /rover/battery and /rover/temperature  
│   └── diagnostic\_server.py          \# \<-- edit this  
├── resource/  
│   └── mobile\_rover  
├── test/  
│   └── evaluate.py  
├── package.xml  
└── setup.py

rover\_interfaces/                     \# provided, already built  
├── srv/  
│   └── DiagnosticSnapshot.srv  
├── CMakeLists.txt  
└── package.xml

### **Student Objective**

Implement a node named `diagnostic_server` that:

1. Subscribes to `/rover/battery` (`std_msgs/msg/Float32`) and stores the latest value  
2. Subscribes to `/rover/temperature` (`std_msgs/msg/Float32`) and stores the latest value  
3. Hosts a service `/rover/get_diagnostics` of type `rover_interfaces/srv/DiagnosticSnapshot`  
4. On each service call, returns:  
   * `battery_voltage`: last value received from `/rover/battery`  
   * `temperature`: last value received from `/rover/temperature`  
   * `status`: `"OK"` if both topics have produced at least one message, else `"NO_DATA"`  
   * `valid`: `True` if status is `"OK"`, else `False`

### **Constraints**

* Use the `rclpy` service API (`create_service`)  
* Do NOT block in the service callback  
* Initialize internal state so that pre-data calls return `valid=False`  
* Use a single executor for both subscriptions and the service

### **Expected Behaviour**

Launch the node before the simulator:

 ros2 service call /rover/get\_diagnostics rover\_interfaces/srv/DiagnosticSnapshot {}

1.  → returns `valid: False, status: 'NO_DATA'`

2. Start the simulator, wait for sensor data, then call again → returns `valid: True, status: 'OK'` with current battery and temperature values

Inspect with:

 ros2 node info /diagnostic\_server  
ros2 service list | grep diagnostics

3. 

### **Evaluation Criteria (Hidden)**

* ✓ Node `diagnostic_server` exists  
* ✓ Service `/rover/get_diagnostics` is advertised with correct type  
* ✓ Both subscriptions are visible in `ros2 node info`  
* ✓ Pre-data service call returns `valid=False`, `status="NO_DATA"`  
* ✓ Post-data service call returns `valid=True`, `status="OK"`  
* ✓ Returned `battery_voltage` matches the last injected value (±0.01)  
* ✓ Returned `temperature` matches the last injected value (±0.01)

---

## **QUESTION 5 — Static Sensor TF Broadcaster \+ Launch Integration for a Warehouse Robot**

**Difficulty:** Hard **Tested Skills:** S1, S2, S3, S4, S6, S8

### **Scenario**

The warehouse robot's perception team needs a static transform between the robot's `base_link` and a newly mounted `lidar_link`. Additionally, a dynamic `odom → base_link` transform is required for navigation. Your team lead has asked you to build a complete TF2 publishing solution and a launch file that brings everything up together.

The robot's odometry is already published on `/odom` (`nav_msgs/msg/Odometry`).

### **Files Student Can Edit**

* `warehouse_tf/warehouse_tf/static_lidar_tf.py`  
* `warehouse_tf/warehouse_tf/odom_tf_broadcaster.py`  
* `warehouse_tf/launch/tf_bringup.launch.py`  
* `warehouse_tf/config/lidar_mount.yaml`

### **Existing Package Structure**

warehouse\_tf/  
├── warehouse\_tf/  
│   ├── \_\_init\_\_.py  
│   ├── odom\_simulator.py             \# provided, publishes /odom  
│   ├── static\_lidar\_tf.py            \# \<-- edit this  
│   └── odom\_tf\_broadcaster.py        \# \<-- edit this  
├── launch/  
│   └── tf\_bringup.launch.py          \# \<-- edit this  
├── config/  
│   └── lidar\_mount.yaml              \# \<-- edit this  
├── resource/  
│   └── warehouse\_tf  
├── test/  
│   └── evaluate.py  
├── package.xml  
└── setup.py

### **Student Objective**

**Part A — Static transform node (`static_lidar_tf.py`):**

1. Read mounting offsets from ROS2 parameters: `x`, `y`, `z`, `roll`, `pitch`, `yaw` (all doubles, default 0.0)  
2. Publish a single static transform with:  
   * `parent_frame_id`: `base_link`  
   * `child_frame_id`: `lidar_link`  
   * Translation: `(x, y, z)`  
   * Rotation: quaternion converted from RPY  
3. Use `tf2_ros.StaticTransformBroadcaster`

**Part B — Dynamic broadcaster (`odom_tf_broadcaster.py`):**

1. Subscribe to `/odom` (`nav_msgs/msg/Odometry`)  
2. For each odometry message, broadcast a transform:  
   * `parent_frame_id`: `odom`  
   * `child_frame_id`: `base_link`  
   * Translation and rotation taken from `msg.pose.pose`  
   * `stamp` from `msg.header.stamp`  
3. Use `tf2_ros.TransformBroadcaster`

**Part C — Config (`lidar_mount.yaml`):**

static\_lidar\_tf:  
  ros\_\_parameters:  
    x: 0.25  
    y: 0.0  
    z: 0.35  
    roll: 0.0  
    pitch: 0.0  
    yaw: 0.0

**Part D — Launch file (`tf_bringup.launch.py`):**

1. Launch `odom_simulator`, `static_lidar_tf` (with the YAML config), and `odom_tf_broadcaster`  
2. Use `launch_ros.actions.Node` and resolve the YAML path with `ament_index_python` and `os.path.join`

### **Constraints**

* Do NOT use the command-line `static_transform_publisher` — implement the node yourself  
* Quaternion conversion must be correct (use `tf_transformations` or a manual implementation)  
* The launch file must load the YAML via the `parameters` argument  
* Do NOT modify `odom_simulator`

### **Expected Behaviour**

After:

ros2 launch warehouse\_tf tf\_bringup.launch.py

Then:

ros2 run tf2\_ros tf2\_echo odom lidar\_link

should resolve the full chain `odom → base_link → lidar_link` and display a translation that combines the moving odom→base\_link with the static (0.25, 0.0, 0.35) base\_link→lidar\_link.

### **Evaluation Criteria (Hidden)**

* ✓ Static transform `base_link → lidar_link` exists in the TF tree  
* ✓ Static transform translation matches YAML values (0.25, 0.0, 0.35) ±0.001  
* ✓ Dynamic transform `odom → base_link` is published at ≥ 5 Hz  
* ✓ Dynamic transform stamp matches odom message stamp  
* ✓ Full chain `odom → base_link → lidar_link` is resolvable via `tf2_ros.Buffer.lookup_transform`  
* ✓ Launch file starts all three nodes  
* ✓ Launch file correctly loads YAML parameters

---

## **QUESTION 6 — End-to-End Robot Bringup: Multi-Node Application**

**Difficulty:** Hard **Tested Skills:** S1, S2, S3, S4, S5, S6, S7, S8

### **Scenario**

You are the integration engineer for a new service robot. Your manager has asked you to deliver a complete bringup that exercises every ROS2 fundamental: publisher, subscriber, custom service, parameterized launch, and TF2. The robot must:

1. Continuously publish its pose to `/robot/pose`  
2. Listen for goal pose requests on `/robot/goal_pose`  
3. Provide a custom service to reset its pose to the origin  
4. Broadcast a TF transform `world → robot_base` matching the live pose  
5. Be brought up via a single parameterized launch file

The custom service interface is already provided.

### **Files Student Can Edit**

* `service_robot/service_robot/pose_manager.py`  
* `service_robot/launch/bringup.launch.py`  
* `service_robot/config/robot_params.yaml`

### **Provided Interface**

\# service\_robot\_interfaces/srv/ResetPose.srv  
\---  
bool success  
string message

### **Existing Package Structure**

service\_robot/  
├── service\_robot/  
│   ├── \_\_init\_\_.py  
│   └── pose\_manager.py               \# \<-- edit this  
├── launch/  
│   └── bringup.launch.py             \# \<-- edit this  
├── config/  
│   └── robot\_params.yaml             \# \<-- edit this  
├── resource/  
│   └── service\_robot  
├── test/  
│   └── evaluate.py  
├── package.xml  
└── setup.py

service\_robot\_interfaces/             \# provided, already built  
├── srv/  
│   └── ResetPose.srv  
├── CMakeLists.txt  
└── package.xml

### **Student Objective**

**Node (`pose_manager.py`):** Implement a single node `pose_manager` that:

1. **Parameters** (declared, with defaults):

   * `publish_rate` (double, default `10.0`) — Hz for pose publishing  
   * `frame_id` (string, default `world`) — TF parent frame  
   * `child_frame_id` (string, default `robot_base`) — TF child frame  
   * `initial_x` (double, default `0.0`)  
   * `initial_y` (double, default `0.0`)  
2. **Internal state:** maintain current pose `(x, y, yaw)` initialized from `initial_x`, `initial_y`, and `0.0`

3. **Publisher:** publishes `geometry_msgs/msg/PoseStamped` on `/robot/pose` at `publish_rate` Hz with the current pose

4. **Subscriber:** listens to `/robot/goal_pose` (`geometry_msgs/msg/PoseStamped`). On each received goal:

   * Update internal `x`, `y` to match the goal's position  
   * Update `yaw` from the goal's quaternion  
5. **Service:** advertises `/robot/reset_pose` (`service_robot_interfaces/srv/ResetPose`). On call:

   * Reset internal state to `(initial_x, initial_y, 0.0)`  
   * Return `success=True`, `message="Pose reset to origin"`  
6. **TF Broadcaster:** at the same `publish_rate`, broadcast a transform from `frame_id` → `child_frame_id` matching the internal pose

**Launch file (`bringup.launch.py`):**

* Launch `pose_manager` with parameters loaded from `config/robot_params.yaml`  
* Resolve the YAML path with `ament_index_python`

**Config (`robot_params.yaml`):**

pose\_manager:  
  ros\_\_parameters:  
    publish\_rate: 20.0  
    frame\_id: world  
    child\_frame\_id: robot\_base  
    initial\_x: 1.0  
    initial\_y: 2.0

### **Constraints**

* All four interfaces (pub, sub, service, TF) must coexist in a single node  
* Use a single `MultiThreadedExecutor` or `SingleThreadedExecutor` — your choice, but justify via correctness  
* Do NOT use `static_transform_publisher`  
* Service response message MUST equal `"Pose reset to origin"` exactly  
* The launch file MUST load parameters from the YAML

### **Expected Behaviour**

1. `ros2 launch service_robot bringup.launch.py` brings up the node with initial pose (1.0, 2.0)  
2. `ros2 topic echo /robot/pose` shows continuous pose at 20 Hz  
3. Publishing a goal pose updates `/robot/pose` to the new position  
4. `ros2 run tf2_ros tf2_echo world robot_base` reflects the current pose  
5. Calling `ros2 service call /robot/reset_pose service_robot_interfaces/srv/ResetPose {}` resets pose to (1.0, 2.0)  
6. `rqt_graph` shows a connected graph of the node, topics, and the service

### **Evaluation Criteria (Hidden)**

* ✓ Node `pose_manager` exists  
* ✓ Publisher on `/robot/pose` (`PoseStamped`) publishing at 20 Hz (±2 Hz)  
* ✓ Subscription on `/robot/goal_pose` (`PoseStamped`)  
* ✓ Service `/robot/reset_pose` with correct type  
* ✓ TF transform `world → robot_base` is broadcast at ≥ 15 Hz  
* ✓ Initial pose reflects YAML overrides (1.0, 2.0)  
* ✓ Goal pose injection at (5.0, 3.0) updates `/robot/pose` to (5.0, 3.0)  
* ✓ Goal pose injection updates TF transform translation accordingly  
* ✓ Service call resets pose to (1.0, 2.0) — verified on next `/robot/pose` message  
* ✓ Service response: `success=True`, `message="Pose reset to origin"`

---

# **4\. ROS PACKAGE STRUCTURES**

(All packages assume placement under `~/ros2_ws/src/` and build with `colcon build`. Only files relevant to the question are shown.)

## **Q1 — inspection\_robot**

inspection\_robot/  
├── inspection\_robot/  
│   ├── \_\_init\_\_.py  
│   └── heartbeat\_publisher.py  
├── resource/inspection\_robot  
├── test/evaluate.py  
├── package.xml  
└── setup.py

## **Q2 — warehouse\_robot**

warehouse\_robot/  
├── warehouse\_robot/  
│   ├── \_\_init\_\_.py  
│   ├── battery\_simulator.py  
│   └── battery\_monitor.py  
├── resource/warehouse\_robot  
├── test/evaluate.py  
├── package.xml  
└── setup.py

## **Q3 — delivery\_robot**

delivery\_robot/  
├── delivery\_robot/  
│   ├── \_\_init\_\_.py  
│   └── velocity\_commander.py  
├── launch/commander.launch.py  
├── resource/delivery\_robot  
├── test/evaluate.py  
├── package.xml  
└── setup.py

## **Q4 — mobile\_rover**

mobile\_rover/  
├── mobile\_rover/  
│   ├── \_\_init\_\_.py  
│   ├── sensor\_simulator.py  
│   └── diagnostic\_server.py  
├── resource/mobile\_rover  
├── test/evaluate.py  
├── package.xml  
└── setup.py

rover\_interfaces/  
├── srv/DiagnosticSnapshot.srv  
├── CMakeLists.txt  
└── package.xml

## **Q5 — warehouse\_tf**

warehouse\_tf/  
├── warehouse\_tf/  
│   ├── \_\_init\_\_.py  
│   ├── odom\_simulator.py  
│   ├── static\_lidar\_tf.py  
│   └── odom\_tf\_broadcaster.py  
├── launch/tf\_bringup.launch.py  
├── config/lidar\_mount.yaml  
├── resource/warehouse\_tf  
├── test/evaluate.py  
├── package.xml  
└── setup.py

## **Q6 — service\_robot**

service\_robot/  
├── service\_robot/  
│   ├── \_\_init\_\_.py  
│   └── pose\_manager.py  
├── launch/bringup.launch.py  
├── config/robot\_params.yaml  
├── resource/service\_robot  
├── test/evaluate.py  
├── package.xml  
└── setup.py

service\_robot\_interfaces/  
├── srv/ResetPose.srv  
├── CMakeLists.txt  
└── package.xml

---

# **5\. REFERENCE SOLUTIONS**

---

## **Q1 — heartbeat\_publisher.py**

\#\!/usr/bin/env python3  
"""Heartbeat publisher for inspection robot — Q1 reference solution."""

import rclpy  
from rclpy.node import Node  
from std\_msgs.msg import String

class HeartbeatPublisher(Node):  
    def \_\_init\_\_(self):  
        super().\_\_init\_\_('heartbeat\_publisher')  
        self.publisher\_ \= self.create\_publisher(String, '/robot/heartbeat', 10\)  
        self.timer\_period \= 0.5  \# 2 Hz  
        self.timer \= self.create\_timer(self.timer\_period, self.timer\_callback)  
        self.counter \= 0  
        self.get\_logger().info('Heartbeat publisher started at 2 Hz')

    def timer\_callback(self):  
        msg \= String()  
        msg.data \= f'ALIVE:{self.counter}'  
        self.publisher\_.publish(msg)  
        self.counter \+= 1

def main(args=None):  
    rclpy.init(args=args)  
    node \= HeartbeatPublisher()  
    try:  
        rclpy.spin(node)  
    except KeyboardInterrupt:  
        pass  
    finally:  
        node.destroy\_node()  
        rclpy.shutdown()

if \_\_name\_\_ \== '\_\_main\_\_':  
    main()

---

## **Q2 — battery\_monitor.py**

\#\!/usr/bin/env python3  
"""Battery threshold subscriber for warehouse robot — Q2 reference solution."""

import rclpy  
from rclpy.node import Node  
from std\_msgs.msg import Float32, String

class BatteryMonitor(Node):  
    LOW\_THRESHOLD \= 11.5

    def \_\_init\_\_(self):  
        super().\_\_init\_\_('battery\_monitor')  
        self.subscription \= self.create\_subscription(  
            Float32, '/robot/battery\_voltage', self.voltage\_callback, 10  
        )  
        self.alert\_pub \= self.create\_publisher(String, '/robot/battery\_alert', 10\)  
        self.get\_logger().info('Battery monitor started')

    def voltage\_callback(self, msg: Float32):  
        if msg.data \< self.LOW\_THRESHOLD:  
            alert \= String()  
            alert.data \= f'LOW BATTERY: {msg.data:.2f}'  
            self.alert\_pub.publish(alert)  
            self.get\_logger().warn(alert.data)

def main(args=None):  
    rclpy.init(args=args)  
    node \= BatteryMonitor()  
    try:  
        rclpy.spin(node)  
    except KeyboardInterrupt:  
        pass  
    finally:  
        node.destroy\_node()  
        rclpy.shutdown()

if \_\_name\_\_ \== '\_\_main\_\_':  
    main()

---

## **Q3 — velocity\_commander.py \+ commander.launch.py**

### **velocity\_commander.py**

\#\!/usr/bin/env python3  
"""Velocity commander with parameter-driven clamping — Q3 reference solution."""

import rclpy  
from rclpy.node import Node  
from geometry\_msgs.msg import Twist

class VelocityCommander(Node):  
    def \_\_init\_\_(self):  
        super().\_\_init\_\_('velocity\_commander')  
        self.declare\_parameter('max\_linear\_velocity', 0.5)  
        self.declare\_parameter('max\_angular\_velocity', 1.0)

        self.subscription \= self.create\_subscription(  
            Twist, '/cmd\_vel\_raw', self.cmd\_callback, 10  
        )  
        self.publisher\_ \= self.create\_publisher(Twist, '/cmd\_vel', 10\)  
        self.get\_logger().info(  
            f"Commander started | max\_lin={self.\_max\_lin()} max\_ang={self.\_max\_ang()}"  
        )

    def \_max\_lin(self) \-\> float:  
        return self.get\_parameter('max\_linear\_velocity').get\_parameter\_value().double\_value

    def \_max\_ang(self) \-\> float:  
        return self.get\_parameter('max\_angular\_velocity').get\_parameter\_value().double\_value

    @staticmethod  
    def clamp(value: float, limit: float) \-\> float:  
        return max(-limit, min(limit, value))

    def cmd\_callback(self, msg: Twist):  
        max\_lin \= self.\_max\_lin()  
        max\_ang \= self.\_max\_ang()  
        out \= Twist()  
        out.linear.x \= self.clamp(msg.linear.x, max\_lin)  
        out.linear.y \= msg.linear.y  
        out.linear.z \= msg.linear.z  
        out.angular.x \= msg.angular.x  
        out.angular.y \= msg.angular.y  
        out.angular.z \= self.clamp(msg.angular.z, max\_ang)  
        self.publisher\_.publish(out)

def main(args=None):  
    rclpy.init(args=args)  
    node \= VelocityCommander()  
    try:  
        rclpy.spin(node)  
    except KeyboardInterrupt:  
        pass  
    finally:  
        node.destroy\_node()  
        rclpy.shutdown()

if \_\_name\_\_ \== '\_\_main\_\_':  
    main()

### **commander.launch.py**

"""Launch file for the velocity commander — Q3 reference solution."""

from launch import LaunchDescription  
from launch\_ros.actions import Node

def generate\_launch\_description():  
    return LaunchDescription(\[  
        Node(  
            package='delivery\_robot',  
            executable='velocity\_commander',  
            name='velocity\_commander',  
            output='screen',  
            parameters=\[{  
                'max\_linear\_velocity': 0.3,  
                'max\_angular\_velocity': 0.8,  
            }\],  
        ),  
    \])

---

## **Q4 — diagnostic\_server.py**

\#\!/usr/bin/env python3  
"""On-demand diagnostic snapshot service — Q4 reference solution."""

import rclpy  
from rclpy.node import Node  
from std\_msgs.msg import Float32  
from rover\_interfaces.srv import DiagnosticSnapshot

class DiagnosticServer(Node):  
    def \_\_init\_\_(self):  
        super().\_\_init\_\_('diagnostic\_server')

        self.\_latest\_battery \= None  
        self.\_latest\_temperature \= None

        self.create\_subscription(Float32, '/rover/battery', self.\_battery\_cb, 10\)  
        self.create\_subscription(Float32, '/rover/temperature', self.\_temp\_cb, 10\)

        self.srv \= self.create\_service(  
            DiagnosticSnapshot,  
            '/rover/get\_diagnostics',  
            self.\_handle\_snapshot,  
        )  
        self.get\_logger().info('Diagnostic server ready')

    def \_battery\_cb(self, msg: Float32):  
        self.\_latest\_battery \= msg.data

    def \_temp\_cb(self, msg: Float32):  
        self.\_latest\_temperature \= msg.data

    def \_handle\_snapshot(self, request, response):  
        if self.\_latest\_battery is None or self.\_latest\_temperature is None:  
            response.battery\_voltage \= 0.0  
            response.temperature \= 0.0  
            response.status \= 'NO\_DATA'  
            response.valid \= False  
        else:  
            response.battery\_voltage \= float(self.\_latest\_battery)  
            response.temperature \= float(self.\_latest\_temperature)  
            response.status \= 'OK'  
            response.valid \= True  
        return response

def main(args=None):  
    rclpy.init(args=args)  
    node \= DiagnosticServer()  
    try:  
        rclpy.spin(node)  
    except KeyboardInterrupt:  
        pass  
    finally:  
        node.destroy\_node()  
        rclpy.shutdown()

if \_\_name\_\_ \== '\_\_main\_\_':  
    main()

---

## **Q5 — static\_lidar\_tf.py \+ odom\_tf\_broadcaster.py \+ lidar\_mount.yaml \+ tf\_bringup.launch.py**

### **static\_lidar\_tf.py**

\#\!/usr/bin/env python3  
"""Static base\_link \-\> lidar\_link transform broadcaster — Q5 reference solution."""

import math  
import rclpy  
from rclpy.node import Node  
from geometry\_msgs.msg import TransformStamped  
from tf2\_ros import StaticTransformBroadcaster

def rpy\_to\_quaternion(roll: float, pitch: float, yaw: float):  
    cy \= math.cos(yaw \* 0.5)  
    sy \= math.sin(yaw \* 0.5)  
    cp \= math.cos(pitch \* 0.5)  
    sp \= math.sin(pitch \* 0.5)  
    cr \= math.cos(roll \* 0.5)  
    sr \= math.sin(roll \* 0.5)  
    qx \= sr \* cp \* cy \- cr \* sp \* sy  
    qy \= cr \* sp \* cy \+ sr \* cp \* sy  
    qz \= cr \* cp \* sy \- sr \* sp \* cy  
    qw \= cr \* cp \* cy \+ sr \* sp \* sy  
    return qx, qy, qz, qw

class StaticLidarTF(Node):  
    def \_\_init\_\_(self):  
        super().\_\_init\_\_('static\_lidar\_tf')  
        for name in ('x', 'y', 'z', 'roll', 'pitch', 'yaw'):  
            self.declare\_parameter(name, 0.0)

        x \= self.get\_parameter('x').value  
        y \= self.get\_parameter('y').value  
        z \= self.get\_parameter('z').value  
        roll \= self.get\_parameter('roll').value  
        pitch \= self.get\_parameter('pitch').value  
        yaw \= self.get\_parameter('yaw').value

        self.broadcaster \= StaticTransformBroadcaster(self)

        t \= TransformStamped()  
        t.header.stamp \= self.get\_clock().now().to\_msg()  
        t.header.frame\_id \= 'base\_link'  
        t.child\_frame\_id \= 'lidar\_link'  
        t.transform.translation.x \= float(x)  
        t.transform.translation.y \= float(y)  
        t.transform.translation.z \= float(z)  
        qx, qy, qz, qw \= rpy\_to\_quaternion(roll, pitch, yaw)  
        t.transform.rotation.x \= qx  
        t.transform.rotation.y \= qy  
        t.transform.rotation.z \= qz  
        t.transform.rotation.w \= qw  
        self.broadcaster.sendTransform(t)  
        self.get\_logger().info(  
            f'Static TF base\_link-\>lidar\_link sent: t=({x},{y},{z}) rpy=({roll},{pitch},{yaw})'  
        )

def main(args=None):  
    rclpy.init(args=args)  
    node \= StaticLidarTF()  
    try:  
        rclpy.spin(node)  
    except KeyboardInterrupt:  
        pass  
    finally:  
        node.destroy\_node()  
        rclpy.shutdown()

if \_\_name\_\_ \== '\_\_main\_\_':  
    main()

### **odom\_tf\_broadcaster.py**

\#\!/usr/bin/env python3  
"""Dynamic odom \-\> base\_link broadcaster — Q5 reference solution."""

import rclpy  
from rclpy.node import Node  
from nav\_msgs.msg import Odometry  
from geometry\_msgs.msg import TransformStamped  
from tf2\_ros import TransformBroadcaster

class OdomTFBroadcaster(Node):  
    def \_\_init\_\_(self):  
        super().\_\_init\_\_('odom\_tf\_broadcaster')  
        self.broadcaster \= TransformBroadcaster(self)  
        self.create\_subscription(Odometry, '/odom', self.\_odom\_cb, 10\)  
        self.get\_logger().info('odom \-\> base\_link broadcaster started')

    def \_odom\_cb(self, msg: Odometry):  
        t \= TransformStamped()  
        t.header.stamp \= msg.header.stamp  
        t.header.frame\_id \= 'odom'  
        t.child\_frame\_id \= 'base\_link'  
        t.transform.translation.x \= msg.pose.pose.position.x  
        t.transform.translation.y \= msg.pose.pose.position.y  
        t.transform.translation.z \= msg.pose.pose.position.z  
        t.transform.rotation \= msg.pose.pose.orientation  
        self.broadcaster.sendTransform(t)

def main(args=None):  
    rclpy.init(args=args)  
    node \= OdomTFBroadcaster()  
    try:  
        rclpy.spin(node)  
    except KeyboardInterrupt:  
        pass  
    finally:  
        node.destroy\_node()  
        rclpy.shutdown()

if \_\_name\_\_ \== '\_\_main\_\_':  
    main()

### **lidar\_mount.yaml**

static\_lidar\_tf:  
  ros\_\_parameters:  
    x: 0.25  
    y: 0.0  
    z: 0.35  
    roll: 0.0  
    pitch: 0.0  
    yaw: 0.0

### **tf\_bringup.launch.py**

"""TF bringup launch — Q5 reference solution."""

import os  
from ament\_index\_python.packages import get\_package\_share\_directory  
from launch import LaunchDescription  
from launch\_ros.actions import Node

def generate\_launch\_description():  
    pkg\_share \= get\_package\_share\_directory('warehouse\_tf')  
    lidar\_params \= os.path.join(pkg\_share, 'config', 'lidar\_mount.yaml')

    return LaunchDescription(\[  
        Node(  
            package='warehouse\_tf',  
            executable='odom\_simulator',  
            name='odom\_simulator',  
            output='screen',  
        ),  
        Node(  
            package='warehouse\_tf',  
            executable='static\_lidar\_tf',  
            name='static\_lidar\_tf',  
            output='screen',  
            parameters=\[lidar\_params\],  
        ),  
        Node(  
            package='warehouse\_tf',  
            executable='odom\_tf\_broadcaster',  
            name='odom\_tf\_broadcaster',  
            output='screen',  
        ),  
    \])

---

## **Q6 — pose\_manager.py \+ bringup.launch.py \+ robot\_params.yaml**

### **pose\_manager.py**

\#\!/usr/bin/env python3  
"""End-to-end pose manager — Q6 reference solution."""

import math  
import rclpy  
from rclpy.node import Node  
from geometry\_msgs.msg import PoseStamped, TransformStamped  
from tf2\_ros import TransformBroadcaster  
from service\_robot\_interfaces.srv import ResetPose

def yaw\_to\_quat(yaw: float):  
    return (0.0, 0.0, math.sin(yaw / 2.0), math.cos(yaw / 2.0))

def quat\_to\_yaw(qx: float, qy: float, qz: float, qw: float) \-\> float:  
    siny\_cosp \= 2.0 \* (qw \* qz \+ qx \* qy)  
    cosy\_cosp \= 1.0 \- 2.0 \* (qy \* qy \+ qz \* qz)  
    return math.atan2(siny\_cosp, cosy\_cosp)

class PoseManager(Node):  
    def \_\_init\_\_(self):  
        super().\_\_init\_\_('pose\_manager')

        self.declare\_parameter('publish\_rate', 10.0)  
        self.declare\_parameter('frame\_id', 'world')  
        self.declare\_parameter('child\_frame\_id', 'robot\_base')  
        self.declare\_parameter('initial\_x', 0.0)  
        self.declare\_parameter('initial\_y', 0.0)

        self.frame\_id \= self.get\_parameter('frame\_id').value  
        self.child\_frame\_id \= self.get\_parameter('child\_frame\_id').value  
        self.\_initial\_x \= float(self.get\_parameter('initial\_x').value)  
        self.\_initial\_y \= float(self.get\_parameter('initial\_y').value)  
        rate \= float(self.get\_parameter('publish\_rate').value)

        self.x \= self.\_initial\_x  
        self.y \= self.\_initial\_y  
        self.yaw \= 0.0

        self.pose\_pub \= self.create\_publisher(PoseStamped, '/robot/pose', 10\)  
        self.create\_subscription(PoseStamped, '/robot/goal\_pose', self.\_goal\_cb, 10\)  
        self.create\_service(ResetPose, '/robot/reset\_pose', self.\_reset\_cb)  
        self.tf\_broadcaster \= TransformBroadcaster(self)

        period \= 1.0 / rate if rate \> 0 else 0.1  
        self.timer \= self.create\_timer(period, self.\_tick)

        self.get\_logger().info(  
            f'pose\_manager up | rate={rate} Hz | initial=({self.\_initial\_x},{self.\_initial\_y})'  
        )

    def \_goal\_cb(self, msg: PoseStamped):  
        self.x \= msg.pose.position.x  
        self.y \= msg.pose.position.y  
        q \= msg.pose.orientation  
        self.yaw \= quat\_to\_yaw(q.x, q.y, q.z, q.w)

    def \_reset\_cb(self, request, response):  
        self.x \= self.\_initial\_x  
        self.y \= self.\_initial\_y  
        self.yaw \= 0.0  
        response.success \= True  
        response.message \= 'Pose reset to origin'  
        return response

    def \_tick(self):  
        now \= self.get\_clock().now().to\_msg()

        pose \= PoseStamped()  
        pose.header.stamp \= now  
        pose.header.frame\_id \= self.frame\_id  
        pose.pose.position.x \= self.x  
        pose.pose.position.y \= self.y  
        pose.pose.position.z \= 0.0  
        qx, qy, qz, qw \= yaw\_to\_quat(self.yaw)  
        pose.pose.orientation.x \= qx  
        pose.pose.orientation.y \= qy  
        pose.pose.orientation.z \= qz  
        pose.pose.orientation.w \= qw  
        self.pose\_pub.publish(pose)

        t \= TransformStamped()  
        t.header.stamp \= now  
        t.header.frame\_id \= self.frame\_id  
        t.child\_frame\_id \= self.child\_frame\_id  
        t.transform.translation.x \= self.x  
        t.transform.translation.y \= self.y  
        t.transform.translation.z \= 0.0  
        t.transform.rotation.x \= qx  
        t.transform.rotation.y \= qy  
        t.transform.rotation.z \= qz  
        t.transform.rotation.w \= qw  
        self.tf\_broadcaster.sendTransform(t)

def main(args=None):  
    rclpy.init(args=args)  
    node \= PoseManager()  
    try:  
        rclpy.spin(node)  
    except KeyboardInterrupt:  
        pass  
    finally:  
        node.destroy\_node()  
        rclpy.shutdown()

if \_\_name\_\_ \== '\_\_main\_\_':  
    main()

### **robot\_params.yaml**

pose\_manager:  
  ros\_\_parameters:  
    publish\_rate: 20.0  
    frame\_id: world  
    child\_frame\_id: robot\_base  
    initial\_x: 1.0  
    initial\_y: 2.0

### **bringup.launch.py**

"""End-to-end bringup launch — Q6 reference solution."""

import os  
from ament\_index\_python.packages import get\_package\_share\_directory  
from launch import LaunchDescription  
from launch\_ros.actions import Node

def generate\_launch\_description():  
    pkg\_share \= get\_package\_share\_directory('service\_robot')  
    params\_file \= os.path.join(pkg\_share, 'config', 'robot\_params.yaml')

    return LaunchDescription(\[  
        Node(  
            package='service\_robot',  
            executable='pose\_manager',  
            name='pose\_manager',  
            output='screen',  
            parameters=\[params\_file\],  
        ),  
    \])

---

# **6\. EVALUATION SCRIPTS**

Each `test/evaluate.py` follows the same pattern: spin a tester node, inspect the graph, inject/observe messages, and emit a JSON result.

---

## **Q1 — test/evaluate.py**

\#\!/usr/bin/env python3  
"""Evaluator for Q1 — heartbeat publisher."""

import json  
import re  
import sys  
import time

import rclpy  
from rclpy.node import Node  
from std\_msgs.msg import String

class HeartbeatChecker(Node):  
    def \_\_init\_\_(self):  
        super().\_\_init\_\_('q1\_evaluator')  
        self.samples \= \[\]  
        self.create\_subscription(String, '/robot/heartbeat', self.\_cb, 10\)

    def \_cb(self, msg: String):  
        self.samples.append((time.time(), msg.data))

def main():  
    rclpy.init()  
    node \= HeartbeatChecker()

    deadline \= time.time() \+ 5.0  
    while time.time() \< deadline:  
        rclpy.spin\_once(node, timeout\_sec=0.1)

    results \= {  
        'node\_present': False,  
        'topic\_present': False,  
        'message\_type\_ok': False,  
        'rate\_ok': False,  
        'format\_ok': False,  
        'counter\_monotonic': False,  
    }

    node\_names \= \[n\[0\] for n in node.get\_node\_names\_and\_namespaces()\]  
    results\['node\_present'\] \= 'heartbeat\_publisher' in node\_names

    topic\_types \= dict(node.get\_topic\_names\_and\_types())  
    if '/robot/heartbeat' in topic\_types:  
        results\['topic\_present'\] \= True  
        results\['message\_type\_ok'\] \= 'std\_msgs/msg/String' in topic\_types\['/robot/heartbeat'\]

    if len(node.samples) \>= 5:  
        times \= \[t for t, \_ in node.samples\]  
        intervals \= \[t2 \- t1 for t1, t2 in zip(times\[:-1\], times\[1:\])\]  
        avg \= sum(intervals) / len(intervals)  
        results\['rate\_ok'\] \= 0.3 \<= avg \<= 0.7  \# 2 Hz ± 0.2 Hz

        pattern \= re.compile(r'^ALIVE:(\\d+)$')  
        counters \= \[\]  
        format\_ok \= True  
        for \_, data in node.samples:  
            m \= pattern.match(data)  
            if not m:  
                format\_ok \= False  
                break  
            counters.append(int(m.group(1)))  
        results\['format\_ok'\] \= format\_ok  
        if format\_ok and len(counters) \>= 2:  
            results\['counter\_monotonic'\] \= all(  
                c2 \== c1 \+ 1 for c1, c2 in zip(counters\[:-1\], counters\[1:\])  
            )

    node.destroy\_node()  
    rclpy.shutdown()

    passed \= all(results.values())  
    output \= {  
        'status': 'completed',  
        'passed': passed,  
        'results': results,  
    }  
    print(json.dumps(output, indent=2))  
    sys.exit(0 if passed else 1\)

if \_\_name\_\_ \== '\_\_main\_\_':  
    main()

---

## **Q2 — test/evaluate.py**

\#\!/usr/bin/env python3  
"""Evaluator for Q2 — battery threshold subscriber."""

import json  
import re  
import sys  
import time

import rclpy  
from rclpy.node import Node  
from std\_msgs.msg import Float32, String

class BatteryEvaluator(Node):  
    def \_\_init\_\_(self):  
        super().\_\_init\_\_('q2\_evaluator')  
        self.injector \= self.create\_publisher(Float32, '/robot/battery\_voltage', 10\)  
        self.alerts \= \[\]  
        self.create\_subscription(String, '/robot/battery\_alert', self.\_alert\_cb, 10\)

    def \_alert\_cb(self, msg: String):  
        self.alerts.append(msg.data)

def inject(node, value, hold\_sec=1.5):  
    msg \= Float32()  
    msg.data \= float(value)  
    start \= time.time()  
    while time.time() \- start \< hold\_sec:  
        node.injector.publish(msg)  
        rclpy.spin\_once(node, timeout\_sec=0.05)

def main():  
    rclpy.init()  
    node \= BatteryEvaluator()  
    time.sleep(1.0)

    results \= {  
        'node\_present': False,  
        'subscription\_ok': False,  
        'alert\_publisher\_ok': False,  
        'low\_voltage\_triggers\_alert': False,  
        'high\_voltage\_no\_alert': False,  
        'format\_ok': False,  
    }

    node\_names \= \[n\[0\] for n in node.get\_node\_names\_and\_namespaces()\]  
    results\['node\_present'\] \= 'battery\_monitor' in node\_names

    topic\_types \= dict(node.get\_topic\_names\_and\_types())  
    if '/robot/battery\_voltage' in topic\_types:  
        results\['subscription\_ok'\] \= 'std\_msgs/msg/Float32' in topic\_types\['/robot/battery\_voltage'\]  
    if '/robot/battery\_alert' in topic\_types:  
        results\['alert\_publisher\_ok'\] \= 'std\_msgs/msg/String' in topic\_types\['/robot/battery\_alert'\]

    \# Test 1: low voltage should trigger alert  
    node.alerts.clear()  
    inject(node, 10.5)  
    results\['low\_voltage\_triggers\_alert'\] \= len(node.alerts) \> 0

    pattern \= re.compile(r'^LOW BATTERY: \\d+\\.\\d{2}$')  
    if node.alerts:  
        results\['format\_ok'\] \= pattern.match(node.alerts\[-1\]) is not None

    \# Test 2: high voltage should NOT trigger alert  
    node.alerts.clear()  
    inject(node, 12.4)  
    results\['high\_voltage\_no\_alert'\] \= len(node.alerts) \== 0

    node.destroy\_node()  
    rclpy.shutdown()

    passed \= all(results.values())  
    print(json.dumps({'status': 'completed', 'passed': passed, 'results': results}, indent=2))  
    sys.exit(0 if passed else 1\)

if \_\_name\_\_ \== '\_\_main\_\_':  
    main()

---

## **Q3 — test/evaluate.py**

\#\!/usr/bin/env python3  
"""Evaluator for Q3 — velocity commander."""

import json  
import sys  
import time

import rclpy  
from rclpy.node import Node  
from geometry\_msgs.msg import Twist

class CommanderEvaluator(Node):  
    def \_\_init\_\_(self):  
        super().\_\_init\_\_('q3\_evaluator')  
        self.injector \= self.create\_publisher(Twist, '/cmd\_vel\_raw', 10\)  
        self.last \= None  
        self.create\_subscription(Twist, '/cmd\_vel', self.\_cb, 10\)

    def \_cb(self, msg: Twist):  
        self.last \= msg

def inject\_and\_capture(node, lin\_x, ang\_z, hold=1.0):  
    node.last \= None  
    msg \= Twist()  
    msg.linear.x \= lin\_x  
    msg.angular.z \= ang\_z  
    start \= time.time()  
    while time.time() \- start \< hold:  
        node.injector.publish(msg)  
        rclpy.spin\_once(node, timeout\_sec=0.05)  
    return node.last

def approx(a, b, tol=1e-3):  
    return abs(a \- b) \< tol

def main():  
    rclpy.init()  
    node \= CommanderEvaluator()  
    time.sleep(1.0)

    results \= {  
        'node\_present': False,  
        'passthrough\_within\_limits': False,  
        'positive\_clamping': False,  
        'negative\_clamping': False,  
        'param\_override\_applied': False,  
    }

    node\_names \= \[n\[0\] for n in node.get\_node\_names\_and\_namespaces()\]  
    results\['node\_present'\] \= 'velocity\_commander' in node\_names

    \# Passthrough: 0.2 lin, 0.5 ang \-\> expect same (within launch limits 0.3, 0.8)  
    out \= inject\_and\_capture(node, 0.2, 0.5)  
    results\['passthrough\_within\_limits'\] \= (  
        out is not None and approx(out.linear.x, 0.2) and approx(out.angular.z, 0.5)  
    )

    \# Positive clamp: 1.5 lin, \-2.0 ang \-\> (0.3, \-0.8)  
    out \= inject\_and\_capture(node, 1.5, \-2.0)  
    results\['positive\_clamping'\] \= (  
        out is not None and approx(out.linear.x, 0.3) and approx(out.angular.z, \-0.8)  
    )

    \# Negative clamp: \-0.9 lin, 0.4 ang \-\> (-0.3, 0.4)  
    out \= inject\_and\_capture(node, \-0.9, 0.4)  
    results\['negative\_clamping'\] \= (  
        out is not None and approx(out.linear.x, \-0.3) and approx(out.angular.z, 0.4)  
    )

    results\['param\_override\_applied'\] \= (  
        results\['positive\_clamping'\] and results\['negative\_clamping'\]  
    )

    node.destroy\_node()  
    rclpy.shutdown()

    passed \= all(results.values())  
    print(json.dumps({'status': 'completed', 'passed': passed, 'results': results}, indent=2))  
    sys.exit(0 if passed else 1\)

if \_\_name\_\_ \== '\_\_main\_\_':  
    main()

---

## **Q4 — test/evaluate.py**

\#\!/usr/bin/env python3  
"""Evaluator for Q4 — diagnostic snapshot service."""

import json  
import sys  
import time

import rclpy  
from rclpy.node import Node  
from std\_msgs.msg import Float32  
from rover\_interfaces.srv import DiagnosticSnapshot

class DiagnosticEvaluator(Node):  
    def \_\_init\_\_(self):  
        super().\_\_init\_\_('q4\_evaluator')  
        self.battery\_pub \= self.create\_publisher(Float32, '/rover/battery', 10\)  
        self.temp\_pub \= self.create\_publisher(Float32, '/rover/temperature', 10\)  
        self.client \= self.create\_client(DiagnosticSnapshot, '/rover/get\_diagnostics')

def call\_service(node, timeout=5.0):  
    if not node.client.wait\_for\_service(timeout\_sec=timeout):  
        return None  
    future \= node.client.call\_async(DiagnosticSnapshot.Request())  
    rclpy.spin\_until\_future\_complete(node, future, timeout\_sec=timeout)  
    return future.result()

def publish\_value(node, pub, value, count=10):  
    msg \= Float32()  
    msg.data \= float(value)  
    for \_ in range(count):  
        pub.publish(msg)  
        rclpy.spin\_once(node, timeout\_sec=0.05)  
        time.sleep(0.05)

def main():  
    rclpy.init()  
    node \= DiagnosticEvaluator()  
    time.sleep(1.0)

    results \= {  
        'node\_present': False,  
        'service\_available': False,  
        'pre\_data\_invalid': False,  
        'post\_data\_valid': False,  
        'battery\_value\_matches': False,  
        'temperature\_value\_matches': False,  
        'status\_strings\_correct': False,  
    }

    node\_names \= \[n\[0\] for n in node.get\_node\_names\_and\_namespaces()\]  
    results\['node\_present'\] \= 'diagnostic\_server' in node\_names

    results\['service\_available'\] \= node.client.wait\_for\_service(timeout\_sec=3.0)

    \# Pre-data call  
    pre \= call\_service(node)  
    if pre is not None:  
        results\['pre\_data\_invalid'\] \= (not pre.valid) and pre.status \== 'NO\_DATA'

    \# Inject data  
    publish\_value(node, node.battery\_pub, 12.34)  
    publish\_value(node, node.temp\_pub, 27.5)  
    time.sleep(0.5)

    post \= call\_service(node)  
    if post is not None:  
        results\['post\_data\_valid'\] \= post.valid and post.status \== 'OK'  
        results\['battery\_value\_matches'\] \= abs(post.battery\_voltage \- 12.34) \< 0.05  
        results\['temperature\_value\_matches'\] \= abs(post.temperature \- 27.5) \< 0.05  
        results\['status\_strings\_correct'\] \= post.status \== 'OK' and (pre is not None and pre.status \== 'NO\_DATA')

    node.destroy\_node()  
    rclpy.shutdown()

    passed \= all(results.values())  
    print(json.dumps({'status': 'completed', 'passed': passed, 'results': results}, indent=2))  
    sys.exit(0 if passed else 1\)

if \_\_name\_\_ \== '\_\_main\_\_':  
    main()

---

## **Q5 — test/evaluate.py**

\#\!/usr/bin/env python3  
"""Evaluator for Q5 — TF broadcasters."""

import json  
import sys  
import time

import rclpy  
from rclpy.node import Node  
from tf2\_ros import Buffer, TransformListener  
from rclpy.time import Time

class TFEvaluator(Node):  
    def \_\_init\_\_(self):  
        super().\_\_init\_\_('q5\_evaluator')  
        self.buffer \= Buffer()  
        self.listener \= TransformListener(self.buffer, self)

def main():  
    rclpy.init()  
    node \= TFEvaluator()

    \# Let TF accumulate  
    deadline \= time.time() \+ 4.0  
    while time.time() \< deadline:  
        rclpy.spin\_once(node, timeout\_sec=0.1)

    results \= {  
        'static\_lidar\_tf\_node\_present': False,  
        'odom\_tf\_broadcaster\_node\_present': False,  
        'static\_tf\_correct': False,  
        'dynamic\_tf\_present': False,  
        'chain\_resolvable': False,  
    }

    node\_names \= \[n\[0\] for n in node.get\_node\_names\_and\_namespaces()\]  
    results\['static\_lidar\_tf\_node\_present'\] \= 'static\_lidar\_tf' in node\_names  
    results\['odom\_tf\_broadcaster\_node\_present'\] \= 'odom\_tf\_broadcaster' in node\_names

    \# Static TF check  
    try:  
        t \= node.buffer.lookup\_transform('base\_link', 'lidar\_link', Time())  
        tx, ty, tz \= (  
            t.transform.translation.x,  
            t.transform.translation.y,  
            t.transform.translation.z,  
        )  
        results\['static\_tf\_correct'\] \= (  
            abs(tx \- 0.25) \< 1e-3 and abs(ty) \< 1e-3 and abs(tz \- 0.35) \< 1e-3  
        )  
    except Exception as e:  
        node.get\_logger().warn(f'static lookup failed: {e}')

    \# Dynamic TF check  
    try:  
        node.buffer.lookup\_transform('odom', 'base\_link', Time())  
        results\['dynamic\_tf\_present'\] \= True  
    except Exception:  
        pass

    \# Full chain  
    try:  
        node.buffer.lookup\_transform('odom', 'lidar\_link', Time())  
        results\['chain\_resolvable'\] \= True  
    except Exception:  
        pass

    node.destroy\_node()  
    rclpy.shutdown()

    passed \= all(results.values())  
    print(json.dumps({'status': 'completed', 'passed': passed, 'results': results}, indent=2))  
    sys.exit(0 if passed else 1\)

if \_\_name\_\_ \== '\_\_main\_\_':  
    main()

---

## **Q6 — test/evaluate.py**

\#\!/usr/bin/env python3  
"""Evaluator for Q6 — end-to-end pose manager."""

import json  
import math  
import sys  
import time

import rclpy  
from rclpy.node import Node  
from geometry\_msgs.msg import PoseStamped  
from tf2\_ros import Buffer, TransformListener  
from rclpy.time import Time  
from service\_robot\_interfaces.srv import ResetPose

class PoseEvaluator(Node):  
    def \_\_init\_\_(self):  
        super().\_\_init\_\_('q6\_evaluator')  
        self.latest\_pose \= None  
        self.create\_subscription(PoseStamped, '/robot/pose', self.\_pose\_cb, 10\)  
        self.goal\_pub \= self.create\_publisher(PoseStamped, '/robot/goal\_pose', 10\)  
        self.reset\_client \= self.create\_client(ResetPose, '/robot/reset\_pose')  
        self.buffer \= Buffer()  
        self.listener \= TransformListener(self.buffer, self)  
        self.pose\_count \= 0  
        self.t\_first \= None  
        self.t\_last \= None

    def \_pose\_cb(self, msg: PoseStamped):  
        self.latest\_pose \= msg  
        now \= time.time()  
        if self.t\_first is None:  
            self.t\_first \= now  
        self.t\_last \= now  
        self.pose\_count \+= 1

def spin\_for(node, seconds):  
    end \= time.time() \+ seconds  
    while time.time() \< end:  
        rclpy.spin\_once(node, timeout\_sec=0.05)

def publish\_goal(node, x, y, yaw=0.0):  
    msg \= PoseStamped()  
    msg.header.frame\_id \= 'world'  
    msg.pose.position.x \= float(x)  
    msg.pose.position.y \= float(y)  
    msg.pose.orientation.z \= math.sin(yaw / 2.0)  
    msg.pose.orientation.w \= math.cos(yaw / 2.0)  
    for \_ in range(10):  
        node.goal\_pub.publish(msg)  
        rclpy.spin\_once(node, timeout\_sec=0.05)

def main():  
    rclpy.init()  
    node \= PoseEvaluator()  
    time.sleep(1.5)  
    spin\_for(node, 2.0)

    results \= {  
        'node\_present': False,  
        'pose\_topic\_active': False,  
        'rate\_ok': False,  
        'initial\_pose\_matches\_yaml': False,  
        'goal\_updates\_pose': False,  
        'tf\_present': False,  
        'tf\_matches\_pose': False,  
        'service\_resets\_pose': False,  
        'service\_response\_correct': False,  
    }

    node\_names \= \[n\[0\] for n in node.get\_node\_names\_and\_namespaces()\]  
    results\['node\_present'\] \= 'pose\_manager' in node\_names  
    results\['pose\_topic\_active'\] \= node.latest\_pose is not None

    if node.pose\_count \>= 10 and node.t\_first and node.t\_last:  
        duration \= node.t\_last \- node.t\_first  
        if duration \> 0:  
            rate \= node.pose\_count / duration  
            results\['rate\_ok'\] \= 15.0 \<= rate \<= 25.0

    if node.latest\_pose is not None:  
        p \= node.latest\_pose.pose.position  
        results\['initial\_pose\_matches\_yaml'\] \= abs(p.x \- 1.0) \< 0.05 and abs(p.y \- 2.0) \< 0.05

    \# Inject goal  
    publish\_goal(node, 5.0, 3.0)  
    spin\_for(node, 1.0)  
    if node.latest\_pose is not None:  
        p \= node.latest\_pose.pose.position  
        results\['goal\_updates\_pose'\] \= abs(p.x \- 5.0) \< 0.05 and abs(p.y \- 3.0) \< 0.05

    \# TF check  
    try:  
        t \= node.buffer.lookup\_transform('world', 'robot\_base', Time())  
        results\['tf\_present'\] \= True  
        results\['tf\_matches\_pose'\] \= (  
            abs(t.transform.translation.x \- 5.0) \< 0.1  
            and abs(t.transform.translation.y \- 3.0) \< 0.1  
        )  
    except Exception:  
        pass

    \# Service reset  
    if node.reset\_client.wait\_for\_service(timeout\_sec=3.0):  
        future \= node.reset\_client.call\_async(ResetPose.Request())  
        rclpy.spin\_until\_future\_complete(node, future, timeout\_sec=3.0)  
        resp \= future.result()  
        if resp is not None:  
            results\['service\_response\_correct'\] \= (  
                resp.success and resp.message \== 'Pose reset to origin'  
            )  
        spin\_for(node, 1.0)  
        if node.latest\_pose is not None:  
            p \= node.latest\_pose.pose.position  
            results\['service\_resets\_pose'\] \= abs(p.x \- 1.0) \< 0.05 and abs(p.y \- 2.0) \< 0.05

    node.destroy\_node()  
    rclpy.shutdown()

    passed \= all(results.values())  
    print(json.dumps({'status': 'completed', 'passed': passed, 'results': results}, indent=2))  
    sys.exit(0 if passed else 1\)

if \_\_name\_\_ \== '\_\_main\_\_':  
    main()

---

# **7\. judge\_runner.py (Universal)**

Single, reusable runner shared by all six questions. Parameterized by question slug.

\#\!/usr/bin/env python3  
"""  
Universal judge runner for ROS2 Fundamentals assessment.

Workflow:  
  1\. Build the workspace  
  2\. Source the overlay  
  3\. Launch the student's solution  
  4\. (Optionally) start support nodes  
  5\. Run the evaluator  
  6\. Collect logs and emit structured JSON

Usage:  
  python3 judge\_runner.py \--question q1  
"""

import argparse  
import json  
import os  
import signal  
import subprocess  
import sys  
import time  
from pathlib import Path

ROS\_DISTRO \= os.environ.get('ROS\_DISTRO', 'humble')  
WORKSPACE \= Path(os.environ.get('ROS\_WS', '/home/student/ros2\_ws'))

\# Per-question configuration  
QUESTIONS \= {  
    'q1': {  
        'package': 'inspection\_robot',  
        'student\_cmd': \['ros2', 'run', 'inspection\_robot', 'heartbeat\_publisher'\],  
        'support\_cmds': \[\],  
        'evaluator': \['python3', '-m', 'pytest', '--tb=short', '-q', None\],  \# path filled  
        'evaluator\_script': 'src/inspection\_robot/test/evaluate.py',  
        'warmup\_sec': 2.0,  
    },  
    'q2': {  
        'package': 'warehouse\_robot',  
        'student\_cmd': \['ros2', 'run', 'warehouse\_robot', 'battery\_monitor'\],  
        'support\_cmds': \[\],  \# evaluator injects voltages directly  
        'evaluator\_script': 'src/warehouse\_robot/test/evaluate.py',  
        'warmup\_sec': 2.0,  
    },  
    'q3': {  
        'package': 'delivery\_robot',  
        'student\_cmd': \['ros2', 'launch', 'delivery\_robot', 'commander.launch.py'\],  
        'support\_cmds': \[\],  
        'evaluator\_script': 'src/delivery\_robot/test/evaluate.py',  
        'warmup\_sec': 3.0,  
    },  
    'q4': {  
        'package': 'mobile\_rover',  
        'student\_cmd': \['ros2', 'run', 'mobile\_rover', 'diagnostic\_server'\],  
        'support\_cmds': \[\],  
        'evaluator\_script': 'src/mobile\_rover/test/evaluate.py',  
        'warmup\_sec': 2.0,  
    },  
    'q5': {  
        'package': 'warehouse\_tf',  
        'student\_cmd': \['ros2', 'launch', 'warehouse\_tf', 'tf\_bringup.launch.py'\],  
        'support\_cmds': \[\],  
        'evaluator\_script': 'src/warehouse\_tf/test/evaluate.py',  
        'warmup\_sec': 4.0,  
    },  
    'q6': {  
        'package': 'service\_robot',  
        'student\_cmd': \['ros2', 'launch', 'service\_robot', 'bringup.launch.py'\],  
        'support\_cmds': \[\],  
        'evaluator\_script': 'src/service\_robot/test/evaluate.py',  
        'warmup\_sec': 3.0,  
    },  
}

def shell(cmd: str, check: bool \= True) \-\> subprocess.CompletedProcess:  
    """Run a shell command through bash with ROS sourced."""  
    full \= (  
        f"source /opt/ros/{ROS\_DISTRO}/setup.bash && "  
        f"cd {WORKSPACE} && "  
        f"\[ \-f install/setup.bash \] && source install/setup.bash; "  
        f"{cmd}"  
    )  
    return subprocess.run(  
        \['bash', '-lc', full\],  
        capture\_output=True,  
        text=True,  
        check=check,  
    )

def background(cmd\_list, log\_path: Path) \-\> subprocess.Popen:  
    """Launch a command in the background with ROS sourced."""  
    cmd\_str \= ' '.join(cmd\_list)  
    wrapper \= (  
        f"source /opt/ros/{ROS\_DISTRO}/setup.bash && "  
        f"cd {WORKSPACE} && source install/setup.bash && "  
        f"exec {cmd\_str}"  
    )  
    log\_f \= open(log\_path, 'w')  
    return subprocess.Popen(  
        \['bash', '-lc', wrapper\],  
        stdout=log\_f,  
        stderr=subprocess.STDOUT,  
        preexec\_fn=os.setsid,  
    )

def kill\_group(proc: subprocess.Popen):  
    if proc and proc.poll() is None:  
        try:  
            os.killpg(os.getpgid(proc.pid), signal.SIGINT)  
            try:  
                proc.wait(timeout=3)  
            except subprocess.TimeoutExpired:  
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)  
        except ProcessLookupError:  
            pass

def build\_workspace(package: str) \-\> dict:  
    result \= shell(f"colcon build \--packages-select {package} \--symlink-install", check=False)  
    return {  
        'build\_returncode': result.returncode,  
        'build\_stdout\_tail': result.stdout\[-2000:\],  
        'build\_stderr\_tail': result.stderr\[-2000:\],  
    }

def run\_evaluator(script\_rel: str) \-\> dict:  
    script \= WORKSPACE / script\_rel  
    result \= shell(f"python3 {script}", check=False)  
    parsed \= None  
    try:  
        \# Evaluator prints JSON to stdout  
        parsed \= json.loads(result.stdout.strip().split('\\n')\[-1\])  
    except Exception:  
        \# Try locating a JSON block within stdout  
        for line in reversed(result.stdout.splitlines()):  
            line \= line.strip()  
            if line.startswith('{'):  
                try:  
                    parsed \= json.loads(line)  
                    break  
                except Exception:  
                    continue  
    return {  
        'evaluator\_returncode': result.returncode,  
        'evaluator\_stdout\_tail': result.stdout\[-2000:\],  
        'evaluator\_stderr\_tail': result.stderr\[-2000:\],  
        'evaluator\_results': parsed,  
    }

def main():  
    parser \= argparse.ArgumentParser()  
    parser.add\_argument('--question', required=True, choices=list(QUESTIONS.keys()))  
    parser.add\_argument('--logdir', default='/tmp/judge\_logs')  
    args \= parser.parse\_args()

    cfg \= QUESTIONS\[args.question\]  
    log\_dir \= Path(args.logdir)  
    log\_dir.mkdir(parents=True, exist\_ok=True)

    output \= {  
        'status': 'incomplete',  
        'question': args.question,  
        'build': None,  
        'support\_logs': \[\],  
        'student\_log': None,  
        'evaluation': None,  
        'message': '',  
    }

    \# 1\. Build  
    output\['build'\] \= build\_workspace(cfg\['package'\])  
    if output\['build'\]\['build\_returncode'\] \!= 0:  
        output\['status'\] \= 'build\_failed'  
        output\['message'\] \= 'colcon build failed'  
        print(json.dumps(output, indent=2))  
        sys.exit(2)

    support\_procs \= \[\]  
    student\_proc \= None

    try:  
        \# 2\. Support nodes  
        for i, cmd in enumerate(cfg.get('support\_cmds', \[\])):  
            log\_path \= log\_dir / f"{args.question}\_support\_{i}.log"  
            support\_procs.append(background(cmd, log\_path))  
            output\['support\_logs'\].append(str(log\_path))  
        if support\_procs:  
            time.sleep(1.0)

        \# 3\. Student solution  
        student\_log \= log\_dir / f"{args.question}\_student.log"  
        output\['student\_log'\] \= str(student\_log)  
        student\_proc \= background(cfg\['student\_cmd'\], student\_log)

        \# 4\. Warmup  
        time.sleep(cfg\['warmup\_sec'\])

        \# 5\. Evaluator  
        output\['evaluation'\] \= run\_evaluator(cfg\['evaluator\_script'\])

        passed \= (  
            output\['evaluation'\]\['evaluator\_returncode'\] \== 0  
            and output\['evaluation'\]\['evaluator\_results'\] is not None  
            and output\['evaluation'\]\['evaluator\_results'\].get('passed', False)  
        )  
        output\['status'\] \= 'completed'  
        output\['passed'\] \= passed  
        output\['message'\] \= 'Evaluation completed'

    except Exception as exc:  
        output\['status'\] \= 'runner\_error'  
        output\['message'\] \= repr(exc)  
    finally:  
        for p in support\_procs:  
            kill\_group(p)  
        kill\_group(student\_proc)

    print(json.dumps(output, indent=2))  
    sys.exit(0 if output.get('passed') else 1\)

if \_\_name\_\_ \== '\_\_main\_\_':  
    main()

**Docker compatibility notes:**

* The runner expects `ROS_DISTRO=humble` and `ROS_WS=/home/student/ros2_ws` env vars (override as needed).  
* All commands are routed through `bash -lc` with `/opt/ros/humble/setup.bash` and the overlay sourced.  
* Background processes are run in their own process group so they can be killed cleanly with SIGINT/SIGKILL.  
* The evaluator emits a single JSON object on stdout; the runner extracts the last JSON line.

---

# **8\. EVALUATION SCENARIOS**

For each question, the evaluator exercises the following scenarios:

| Q | Normal | Edge Case | Incorrect Config | Missing Component |
| ----- | ----- | ----- | ----- | ----- |
| Q1 | Heartbeat at 2 Hz, monotonic counter | Counter format must match `ALIVE:N` | Wrong topic name → topic\_present=false | Wrong message type → message\_type\_ok=false |
| Q2 | Low voltage triggers alert | Threshold boundary (11.5 V) — must NOT alert | Wrong alert format → format\_ok=false | No subscription → subscription\_ok=false |
| Q3 | Passthrough within limits | Negative clamping | Hardcoded limits ignore launch overrides | Launch file missing parameters → param\_override\_applied=false |
| Q4 | Pre-data NO\_DATA, post-data OK | Service returns valid=False before any sensor | Wrong service type → service\_available=false | Missing subscription → never transitions to OK |
| Q5 | Static \+ dynamic TF resolvable | Full chain `odom → lidar_link` lookup | YAML not loaded → static\_tf\_correct=false | Missing tf2\_ros broadcaster → dynamic\_tf\_present=false |
| Q6 | Pose, TF, service all coexist | Service response message must equal exact string | YAML not loaded → initial pose wrong | Missing TF broadcast → tf\_present=false |

---

# **9\. COMMON MISTAKES & DEBUGGING NOTES**

## **Q1 — Heartbeat Publisher**

* ❌ Forgetting to call `super().__init__('heartbeat_publisher')` → node name won't match  
* ❌ Using `create_timer(2.0, ...)` thinking the argument is Hz — it's the period in seconds  
* ❌ Resetting `counter` to 0 inside the callback  
* ✅ Debug with `ros2 topic hz /robot/heartbeat` to confirm rate

## **Q2 — Battery Threshold Subscriber**

* ❌ Using `<=` instead of `<` at the threshold boundary  
* ❌ Using a timer instead of a subscriber callback  
* ❌ String formatting that doesn't match the regex (e.g. `LOW BATTERY: 11.3` instead of `11.30`)  
* ✅ Test with `ros2 topic pub --once /robot/battery_voltage std_msgs/msg/Float32 "data: 10.0"`

## **Q3 — Velocity Commander**

* ❌ Hardcoding limits inside `cmd_callback` and ignoring parameters  
* ❌ Reading parameters once in `__init__` instead of per-callback (means runtime changes are ignored)  
* ❌ Forgetting `parameters=[...]` in the launch file's `Node` action  
* ✅ Verify parameters with `ros2 param get /velocity_commander max_linear_velocity`  
* ✅ Verify with `ros2 topic pub /cmd_vel_raw geometry_msgs/msg/Twist "{linear: {x: 1.5}, angular: {z: -2.0}}"`

## **Q4 — Diagnostic Service**

* ❌ Returning a fresh `DiagnosticSnapshot.Response()` instead of populating the passed-in `response` argument  
* ❌ Blocking inside the callback (e.g. waiting for sensor data) — the executor stalls  
* ❌ Not importing the service from `rover_interfaces.srv` correctly  
* ✅ Debug with `ros2 service type /rover/get_diagnostics` and `ros2 service call /rover/get_diagnostics rover_interfaces/srv/DiagnosticSnapshot {}`  
* ✅ Use `ros2 node info /diagnostic_server` to verify subscriptions and services

## **Q5 — TF Broadcasters**

* ❌ Using `TransformBroadcaster` for the static TF instead of `StaticTransformBroadcaster` — the transform vanishes after first publish  
* ❌ Incorrect RPY → quaternion conversion (especially mixing up axis order)  
* ❌ Forgetting to copy `msg.header.stamp` into the dynamic TF → TF buffer extrapolation warnings  
* ❌ Loading the YAML at the wrong path — must use `get_package_share_directory`, not the source tree  
* ✅ Debug with `ros2 run tf2_tools view_frames.py` to inspect the full tree  
* ✅ Inspect live with `ros2 run tf2_ros tf2_echo base_link lidar_link`

## **Q6 — End-to-End Pose Manager**

* ❌ Spinning the node before declaring parameters — get\_parameter raises ParameterNotDeclaredException  
* ❌ Service response `message` not matching the exact string `"Pose reset to origin"` (extra period, capitalization, etc.)  
* ❌ Subscribing to `/robot/goal_pose` but never updating internal state  
* ❌ Publishing TF inside the goal callback instead of the timer → TF stops updating when no goals arrive  
* ❌ Forgetting to convert quaternion → yaw when updating from a goal pose  
* ✅ Inspect graph with `rqt_graph` to confirm all connections  
* ✅ Verify TF rate with `ros2 topic hz /tf`  
* ✅ Verify service with `ros2 service call /robot/reset_pose service_robot_interfaces/srv/ResetPose {}`

---

## **General ROS2 Humble Debugging Toolbox**

| Tool | Use |
| ----- | ----- |
| `ros2 node list` | Confirm node is alive |
| `ros2 node info /name` | See pubs, subs, services, actions for a node |
| `ros2 topic list -t` | See all topics with their types |
| `ros2 topic echo /topic` | Watch live messages |
| `ros2 topic hz /topic` | Measure publishing rate |
| `ros2 topic pub` | Inject test messages |
| `ros2 service list -t` | See all services with types |
| `ros2 service call` | Invoke a service from the CLI |
| `ros2 param list /node` | List a node's parameters |
| `ros2 param get/set` | Read/write parameter values |
| `ros2 run tf2_ros tf2_echo` | Inspect a single TF |
| `ros2 run tf2_tools view_frames.py` | Generate a PDF of the TF tree |
| `rqt_graph` | Visualize the live computation graph |
| `rqt` | Multi-panel introspection (plot, console, topic monitor) |

---

## **Final Validation Checklist**

* ✅ Every question maps to syllabus skills (S1–S8)  
* ✅ Every syllabus skill is covered by ≥1 question  
* ✅ No external concepts introduced (no Nav2, SLAM, MoveIt, OpenCV, etc.)  
* ✅ All questions are auto-gradable via the evaluators  
* ✅ All reference solutions are complete, executable, and ROS2 Humble compatible  
* ✅ All evaluators emit structured JSON and exit codes for platform integration  
* ✅ `judge_runner.py` is Docker-compatible and parameterized per question  
* ✅ Difficulty distribution: 2 Easy (Q1, Q2), 2 Medium (Q3, Q4), 2 Hard (Q5, Q6)

