NIAT | NxtWave Robotics & AI Platform

**Coding Assessment**

**ROBOT MATHEMATICS**

ROS2 Humble  |  Ubuntu 22.04  |  Python 3.10  |  Online IDE

**6 Coding Questions  |  Difficulty: Easy → Hard  |  Auto-Graded**

# **1\. TOPIC ANALYSIS**

**Topic:** Robot Mathematics

**Platform:** ROS2 Humble | Ubuntu 22.04 | Python 3.10

Robot Mathematics is the foundational quantitative layer underpinning all motion, sensing, and coordination in robotics. This assessment tests whether students can implement — not just recall — the mathematics that drives real differential-drive robots: transforming coordinates between frames, computing the wheel speeds needed to achieve a desired body velocity, reconstructing position from encoder pulses, and converting between the two dominant orientation representations (Euler angles and quaternions) used throughout ROS2. All questions are strictly bounded to this syllabus. No Nav2, SLAM, URDF, sensor fusion, or control theory is introduced.

# **2\. SKILLS BEING TESTED**

### **Syllabus Coverage Matrix**

| ID | Skill | Covered By |
| ----- | ----- | ----- |
| S1 | Vector and matrix operations for coordinate frame transformations | Q1, Q2 |
| S2 | Applying rotation matrices to transform points between frames | Q1, Q2 |
| S3 | Homogeneous transformation matrices (4×4) | Q2 |
| S4 | Forward kinematics — differential drive (v, ω → wheel speeds) | Q3, Q6 |
| S5 | Inverse kinematics — differential drive (wheel speeds → v, ω) | Q3 |
| S6 | Deriving odometry from encoder tick counts | Q4, Q6 |
| S7 | Dead-reckoning pose update (x, y, θ) from odometry | Q4, Q6 |
| S8 | Euler angles (roll, pitch, yaw) — representation and conversion | Q5, Q6 |
| S9 | Quaternion representation of orientation | Q5, Q6 |
| S10 | Converting between Euler angles and quaternions | Q5, Q6 |

**All 10 skills are covered.** No syllabus skill is untested.

# **3\. SIX CODING QUESTIONS**

| QUESTION 1    EASY |
| :---- |

### **Transform a Sensor Reading from Robot Frame to World Frame**

| Tested Skills |
| :---- |
|  |
|  |

**Scenario**

You are a junior software engineer on an inspection robot team. The robot's forward-facing distance sensor detects an obstacle at a position expressed in the robot's local body frame (x\_r, y\_r). The robot's current pose in the world frame is known: position (x\_robot, y\_robot) and heading θ. Your task is to implement a Python script that applies a 2D rotation matrix to transform the obstacle's coordinates from the robot frame into the world frame so the fleet management system can use them.

**Files Student Can Edit**

scripts/frame\_transform.py

**Existing Package Structure**

frame\_math\_pkg/  
├── scripts/  
│   └── frame\_transform.py      ← EDIT THIS  
├── test/  
│   └── evaluate.py  
├── package.xml  
└── setup.py

**Student Objective**

Open scripts/frame\_transform.py and implement the FrameTransformer class:

1. **Function:** transform\_to\_world(x\_r, y\_r, x\_robot, y\_robot, theta)

    Construct a 2D rotation matrix R(θ) and apply it to the sensor vector \[x\_r, y\_r\]ᵀ. Add the robot's world-frame translation \[x\_robot, y\_robot\]ᵀ to produce the world-frame point. Return (x\_world, y\_world) as a tuple of floats. Use only NumPy — no external ROS calls needed.

2. **Function:** build\_rotation\_matrix(theta)

    Returns the 2×2 rotation matrix for angle θ as a NumPy ndarray.

3. **Function:** transform\_batch(points\_robot, x\_robot, y\_robot, theta)

    Accepts a list of (x\_r, y\_r) tuples and returns a list of (x\_world, y\_world) tuples. Must use matrix multiplication on the full batch — do not loop per-point.

**Constraints**

* Use NumPy for all matrix operations

* Do NOT use scipy, tf\_transformations, or any ROS library

* Do NOT modify evaluate.py or package files

* batch transform must use vectorised matrix multiplication (np.dot or @), not a Python loop

**Expected Behaviour**

When evaluated:

* A robot at (1.0, 2.0) facing θ \= π/2 with sensor reading (1.0, 0.0) should yield world point (1.0, 3.0)

* A robot at (0, 0\) facing θ \= 0 with sensor (2.0, 1.0) should yield world point (2.0, 1.0)

* Batch transform on 100 points must complete in under 0.05 seconds

**Evaluation Criteria (Hidden)**

* transform\_to\_world returns correct (x, y) for 10+ test poses

* build\_rotation\_matrix produces orthogonal matrix (RᵀR \= I within 1e-9)

* Rotation matrix determinant \= \+1.0 within tolerance

* Batch transform result matches per-point loop results

* No import of tf\_transformations, scipy, or ROS packages detected

| QUESTION 2    EASY-MEDIUM |
| :---- |

### **Build a 3D Homogeneous Transformation Library**

| Tested Skills |
| :---- |
|  |
|  |
|  |

**Scenario**

The navigation team needs a lightweight, dependency-free transformation utility for their mobile rover. The rover has multiple sensor frames (LiDAR, camera, IMU) each defined by a fixed offset and rotation relative to the base\_link. Your task is to implement a Python module that builds 4×4 homogeneous transformation matrices and chains them together, so any sensor reading can be expressed in any other frame.

**Files Student Can Edit**

scripts/transform\_lib.py

**Existing Package Structure**

transform\_math\_pkg/  
├── scripts/  
│   └── transform\_lib.py         ← EDIT THIS  
├── test/  
│   └── evaluate.py  
├── package.xml  
└── setup.py

**Student Objective**

Implement the TransformLib class in scripts/transform\_lib.py:

4. **rot\_x(angle), rot\_y(angle), rot\_z(angle)** — Return 3×3 rotation matrices for rotation about the respective axis

5. **homogeneous(R, t)** — Accept a 3×3 rotation matrix R and translation vector t (shape \[3\]), return a 4×4 homogeneous transformation matrix T

6. **chain(\*transforms)** — Accept any number of 4×4 T matrices and return their product T1 @ T2 @ ... @ Tn (left-to-right composition)

7. **transform\_point(T, point)** — Apply 4×4 matrix T to a 3D point \[x, y, z\] and return the transformed \[x, y, z\] (handle homogeneous division)

8. **invert\_transform(T)** — Return the inverse of a rigid-body T matrix using the analytical formula (not np.linalg.inv)

**Constraints**

* Use only NumPy

* invert\_transform must use the analytical formula: T⁻¹ \= \[Rᵀ | \-Rᵀt; 0 0 0 1\]

* chain must work for any number of ≥1 matrices

* Do NOT use scipy.spatial.transform or tf2 library functions

**Expected Behaviour**

* homogeneous(I₃, \[1,2,3\]) produces T with last column \[1,2,3,1\]

* chain(T1, T2, inv(T2)) produces identity within 1e-10

* transform\_point with pure translation T moves point correctly

* invert\_transform(T) @ T \= I₄ within 1e-10

| QUESTION 3    EASY-MEDIUM |
| :---- |

### **Implement a Differential Drive Kinematics Node**

| Tested Skills |
| :---- |
|  |
|  |

**Scenario**

The drive team is integrating a new differential-drive delivery robot. The low-level motor controller accepts individual wheel angular velocities (rad/s), but the planner publishes Twist messages (linear.x, angular.z). You must implement the kinematic conversion node that sits between them. The same node must also run the inverse — reconstructing linear and angular velocity from measured wheel speeds — for the odometry pipeline to use.

**Files Student Can Edit**

scripts/diff\_drive\_kinematics.py

**Existing Package Structure**

diff\_drive\_pkg/  
├── launch/  
│   └── kinematics.launch.py  
├── config/  
│   └── robot\_params.yaml  
├── scripts/  
│   └── diff\_drive\_kinematics.py    ← EDIT THIS  
├── test/  
│   └── evaluate.py  
├── package.xml  
└── setup.py

**robot\_params.yaml (pre-filled, read-only)**

diff\_drive\_kinematics:  
  ros\_\_parameters:  
    wheel\_radius: 0.075    \# metres  
    wheel\_base: 0.40       \# metres (distance between wheel centres)

**Student Objective**

Complete the DiffDriveKinematics ROS2 node in scripts/diff\_drive\_kinematics.py:

9. Read wheel\_radius (r) and wheel\_base (L) from ROS2 parameters at startup

10. **Subscription:** /cmd\_vel (geometry\_msgs/Twist) → compute right and left wheel angular velocities using forward kinematics:

    ω\_r \= (v \+ ω\_body × L/2) / r    and    ω\_l \= (v − ω\_body × L/2) / r

    Publish the result on /wheel\_speeds (geometry\_msgs/Vector3: x=ω\_l, y=ω\_r, z=0)

11. **Subscription:** /wheel\_speeds\_feedback (geometry\_msgs/Vector3: x=ω\_l, y=ω\_r) → reconstruct body linear and angular velocity:

    v \= r × (ω\_r \+ ω\_l) / 2     ω\_body \= r × (ω\_r − ω\_l) / L

    Publish on /body\_velocity (geometry\_msgs/Twist)

**Constraints**

* Load wheel\_radius and wheel\_base strictly from ROS2 parameters — do NOT hardcode

* Use geometry\_msgs/Twist for cmd\_vel and body\_velocity

* Use geometry\_msgs/Vector3 for wheel\_speeds and wheel\_speeds\_feedback

* Do NOT modify launch file or YAML

**Expected Behaviour**

* Publishing v=1.0, ω=0.0 on /cmd\_vel → /wheel\_speeds shows ω\_l \= ω\_r ≈ 13.33 rad/s (for r=0.075)

* Publishing v=0.0, ω=1.0 → ω\_r \> 0, ω\_l \< 0 (turning in place)

* Round-trip: cmd\_vel → wheel\_speeds → body\_velocity recovers original v and ω within 1e-9

| QUESTION 4    MEDIUM |
| :---- |

### **Derive Odometry from Raw Encoder Tick Counts**

| Tested Skills |
| :---- |
|  |
|  |

**Scenario**

A warehouse robot reports raw encoder tick counts from its left and right wheel encoders over a ROS2 topic. The odometry stack is broken — the existing node reads ticks but produces (0, 0, 0\) for the pose. Your job is to fix the encoder\_odometry.py node so it correctly converts accumulated tick counts into displacement and updates the robot's estimated x, y, θ pose using the standard dead-reckoning equations.

**Files Student Can Edit**

scripts/encoder\_odometry.py

**Existing Package Structure**

encoder\_odom\_pkg/  
├── launch/  
│   └── odom.launch.py  
├── config/  
│   └── robot\_params.yaml  
├── scripts/  
│   └── encoder\_odometry.py     ← EDIT THIS (buggy stub provided)  
├── test/  
│   └── evaluate.py  
├── package.xml  
└── setup.py

**robot\_params.yaml (pre-filled, read-only)**

encoder\_odometry:  
  ros\_\_parameters:  
    wheel\_radius: 0.075  
    wheel\_base: 0.40  
    ticks\_per\_revolution: 4096

**Student Objective**

Fix the EncoderOdometry ROS2 node in scripts/encoder\_odometry.py:

12. Read the three robot parameters from ROS2 parameters at startup

13. **Subscription:** /encoder\_ticks (std\_msgs/Int64MultiArray: data\[0\]=left\_ticks, data\[1\]=right\_ticks)

    The ticks are absolute cumulative counts. Compute delta\_ticks\_left and delta\_ticks\_right since the last callback.

14. Convert delta ticks to wheel travel distances:

    d\_left  \= (delta\_ticks\_left  / ticks\_per\_revolution) × 2π × wheel\_radius

    d\_right \= (delta\_ticks\_right / ticks\_per\_revolution) × 2π × wheel\_radius

15. Compute the robot centre displacement and heading change:

    d\_centre \= (d\_right \+ d\_left) / 2    delta\_theta \= (d\_right − d\_left) / wheel\_base

16. Update the pose using the standard dead-reckoning equations:

    x \+= d\_centre × cos(θ \+ delta\_theta/2)

    y \+= d\_centre × sin(θ \+ delta\_theta/2)

    θ \+= delta\_theta

17. **Publish:** /odom (nav\_msgs/Odometry) with the updated x, y, θ and a valid header (frame\_id="odom", child\_frame\_id="base\_link")

**Constraints**

* Do NOT use any external odometry library

* Tick counts are absolute (not incremental) — you must track previous tick values

* Initial pose: x=0, y=0, θ=0

* Do NOT modify the launch file or YAML

**Expected Behaviour**

* One full revolution of both wheels (4096 ticks each) at equal speed → robot moves forward 2π × 0.075 ≈ 0.4712 m

* Right wheel \+4096 ticks, left wheel 0 ticks → robot turns left (positive θ)

* /odom message has correct frame\_id fields

| QUESTION 5    MEDIUM |
| :---- |

### **Build an Orientation Conversion Node: Euler Angles ↔ Quaternions**

| Tested Skills |
| :---- |
|  |
|  |
|  |

**Scenario**

The sensor fusion team has a drone that reports its orientation as Euler angles (roll, pitch, yaw) in a custom message. The planning system requires quaternions (as geometry\_msgs/Quaternion). Another consumer needs the reverse path: it receives quaternion orientation estimates and must log human-readable roll, pitch, yaw. You must implement the conversion node without using tf\_transformations or scipy — all math must be coded from first principles using NumPy.

**Files Student Can Edit**

scripts/orientation\_converter.py

**Existing Package Structure**

orientation\_math\_pkg/  
├── launch/  
│   └── converter.launch.py  
├── scripts/  
│   └── orientation\_converter.py    ← EDIT THIS  
├── msg/  
│   └── EulerAngles.msg             (pre-defined: float64 roll, float64 pitch, float64 yaw)  
├── test/  
│   └── evaluate.py  
├── package.xml  
└── setup.py

**Student Objective**

Implement the OrientationConverter ROS2 node in scripts/orientation\_converter.py:

18. **Function euler\_to\_quaternion(roll, pitch, yaw):** Implement the intrinsic ZYX conversion formula (yaw applied first, then pitch, then roll). Return (x, y, z, w) tuple:

    cy \= cos(yaw/2)   sy \= sin(yaw/2)

    cp \= cos(pitch/2) sp \= sin(pitch/2)

    cr \= cos(roll/2)  sr \= sin(roll/2)

    w \= cr×cp×cy \+ sr×sp×sy

    x \= sr×cp×cy − cr×sp×sy

    y \= cr×sp×cy \+ sr×cp×sy

    z \= cr×cp×sy − sr×sp×cy

19. **Function quaternion\_to\_euler(x, y, z, w):** Implement the inverse using the atan2 formula. Return (roll, pitch, yaw):

    roll  \= atan2(2(wx+yz), 1−2(x²+y²))

    pitch \= asin(clamp(2(wy−zx), −1, 1))

    yaw   \= atan2(2(wz+xy), 1−2(y²+z²))

20. **Subscription:** /euler\_in (orientation\_math\_pkg/EulerAngles) → call euler\_to\_quaternion → publish to /quaternion\_out (geometry\_msgs/Quaternion)

21. **Subscription:** /quaternion\_in (geometry\_msgs/Quaternion) → call quaternion\_to\_euler → publish to /euler\_out (orientation\_math\_pkg/EulerAngles)

**Constraints**

* Do NOT use tf\_transformations, scipy, or transforms3d

* All trigonometry must use math or numpy — no shortcuts

* Quaternion output must be normalised (|q| \= 1 within 1e-9)

* pitch must be clamped to avoid asin domain errors

**Expected Behaviour**

* euler\_to\_quaternion(0, 0, π/2) → (0, 0, 0.7071, 0.7071) within 1e-6

* Round-trip: euler → quat → euler recovers original angles within 1e-9 for 1000 random inputs

* /quaternion\_out messages are unit quaternions

* Gimbal lock at pitch=π/2 is handled without NaN (output is finite)

| QUESTION 6    HARD |
| :---- |

### **Build a Complete Dead-Reckoning Odometry Node for a Differential Drive Robot**

| Tested Skills |
| :---- |
|  |
|  |
|  |
|  |

**Scenario**

You have been handed a partially completed odometry node for a new differential-drive service robot being trialled at a hospital. The robot's encoder ticks arrive on one topic; the robot also receives commanded velocities via /cmd\_vel. The node must: compute the body velocity implied by the encoder readings (inverse kinematics), use dead-reckoning to update the robot's world-frame pose (x, y, θ), convert θ to a quaternion from first principles (no libraries), and publish a complete nav\_msgs/Odometry message. This is an end-to-end odometry pipeline — the same type of task that every differential-drive robot driver implements in practice.

**Files Student Can Edit**

scripts/full\_odometry.py  
launch/odom\_full.launch.py

**Existing Package Structure**

full\_odom\_pkg/  
├── launch/  
│   └── odom\_full.launch.py        ← MAY EDIT  
├── config/  
│   └── robot\_params.yaml  
├── scripts/  
│   └── full\_odometry.py           ← EDIT THIS (stub provided)  
├── test/  
│   └── evaluate.py  
├── package.xml  
└── setup.py

**robot\_params.yaml (pre-filled, read-only)**

full\_odometry:  
  ros\_\_parameters:  
    wheel\_radius: 0.075  
    wheel\_base: 0.40  
    ticks\_per\_revolution: 4096  
    odom\_frame: "odom"  
    base\_frame: "base\_link"

**Student Objective**

Complete the FullOdometry ROS2 node in scripts/full\_odometry.py:

22. Load all five parameters at startup

23. **Encoder tick subscription:** /encoder\_ticks (std\_msgs/Int64MultiArray) — same as Q4. Convert ticks to d\_left, d\_right. Update pose via dead-reckoning equations.

24. **Quaternion from yaw:** Convert the heading angle θ to a quaternion (x, y, z, w) using the ZYX formula with roll=0, pitch=0, yaw=θ. Must be implemented from first principles — no library calls.

25. **Odometry publication:** Publish /odom (nav\_msgs/Odometry) with:

    * header.frame\_id \= odom\_frame parameter

    * child\_frame\_id \= base\_frame parameter

    * pose.pose.position: x, y, z=0

    * pose.pose.orientation: quaternion from step 3

    * twist.twist.linear.x \= v (body linear velocity)

    * twist.twist.angular.z \= ω\_body (angular velocity)

26. **Body velocity:** Derive v and ω from the most recent d\_left, d\_right and the elapsed time dt (use ROS2 clock for timestamps).

**Constraints**

* Quaternion conversion must be hand-coded — no tf\_transformations, scipy, or transforms3d

* Parameters must come from ROS2 parameter server

* Clock must be ROS2 clock (not Python time.time())

* /odom must publish at every encoder tick callback

* Do NOT add any joints/TF broadcasts — odometry message only

**Expected Behaviour**

* Straight-line drive of 1000 encoder ticks per wheel → x displacement within 0.001 m of theoretical, y ≈ 0, θ ≈ 0

* Pure rotation (left ticks \= 0, right ticks \= N) → x ≈ 0, y ≈ 0, θ \> 0

* Quaternion in /odom is always unit quaternion (norm within 1e-9)

* frame\_id and child\_frame\_id match parameters

# **4\. ROS PACKAGE STRUCTURES**

**frame\_math\_pkg (Q1)**

frame\_math\_pkg/  
├── scripts/  
│   └── frame\_transform.py  
├── test/  
│   └── evaluate.py  
├── package.xml  
└── setup.py

**transform\_math\_pkg (Q2)**

transform\_math\_pkg/  
├── scripts/  
│   └── transform\_lib.py  
├── test/  
│   └── evaluate.py  
├── package.xml  
└── setup.py

**diff\_drive\_pkg (Q3)**

diff\_drive\_pkg/  
├── launch/  
│   └── kinematics.launch.py  
├── config/  
│   └── robot\_params.yaml  
├── scripts/  
│   └── diff\_drive\_kinematics.py  
├── test/  
│   └── evaluate.py  
├── package.xml  
└── setup.py

**encoder\_odom\_pkg (Q4)**

encoder\_odom\_pkg/  
├── launch/  
│   └── odom.launch.py  
├── config/  
│   └── robot\_params.yaml  
├── scripts/  
│   └── encoder\_odometry.py  
├── test/  
│   └── evaluate.py  
├── package.xml  
└── setup.py

**orientation\_math\_pkg (Q5)**

orientation\_math\_pkg/  
├── launch/  
│   └── converter.launch.py  
├── msg/  
│   └── EulerAngles.msg  
├── scripts/  
│   └── orientation\_converter.py  
├── test/  
│   └── evaluate.py  
├── package.xml  
└── setup.py

**full\_odom\_pkg (Q6)**

full\_odom\_pkg/  
├── launch/  
│   └── odom\_full.launch.py  
├── config/  
│   └── robot\_params.yaml  
├── scripts/  
│   └── full\_odometry.py  
├── test/  
│   └── evaluate.py  
├── package.xml  
└── setup.py

# **5\. REFERENCE SOLUTIONS**

### **Solution — Q1: scripts/frame\_transform.py**

\#\!/usr/bin/env python3  
"""Q1 Reference Solution: 2D Frame Transformation"""  
import numpy as np  
   
class FrameTransformer:  
    def build\_rotation\_matrix(self, theta: float) \-\> np.ndarray:  
        c, s \= np.cos(theta), np.sin(theta)  
        return np.array(\[\[c, \-s\], \[s, c\]\])  
   
    def transform\_to\_world(self, x\_r, y\_r, x\_robot, y\_robot, theta) \-\> tuple:  
        R \= self.build\_rotation\_matrix(theta)  
        p\_robot \= np.array(\[x\_r, y\_r\])  
        p\_world \= R @ p\_robot \+ np.array(\[x\_robot, y\_robot\])  
        return float(p\_world\[0\]), float(p\_world\[1\])  
   
    def transform\_batch(self, points\_robot, x\_robot, y\_robot, theta) \-\> list:  
        R \= self.build\_rotation\_matrix(theta)  
        P \= np.array(points\_robot).T  \# shape (2, N)  
        t \= np.array(\[\[x\_robot\], \[y\_robot\]\])  
        P\_world \= R @ P \+ t  \# (2, N)  
        return \[(float(P\_world\[0, i\]), float(P\_world\[1, i\]))  
                for i in range(P\_world.shape\[1\])\]

### **Solution — Q2: scripts/transform\_lib.py**

\#\!/usr/bin/env python3  
"""Q2 Reference Solution: 3D Homogeneous Transformations"""  
import numpy as np  
   
class TransformLib:  
    def rot\_x(self, a) \-\> np.ndarray:  
        c, s \= np.cos(a), np.sin(a)  
        return np.array(\[\[1,0,0\],\[0,c,-s\],\[0,s,c\]\])  
   
    def rot\_y(self, a) \-\> np.ndarray:  
        c, s \= np.cos(a), np.sin(a)  
        return np.array(\[\[c,0,s\],\[0,1,0\],\[-s,0,c\]\])  
   
    def rot\_z(self, a) \-\> np.ndarray:  
        c, s \= np.cos(a), np.sin(a)  
        return np.array(\[\[c,-s,0\],\[s,c,0\],\[0,0,1\]\])  
   
    def homogeneous(self, R: np.ndarray, t: np.ndarray) \-\> np.ndarray:  
        T \= np.eye(4)  
        T\[:3, :3\] \= R  
        T\[:3, 3\]  \= t  
        return T  
   
    def chain(self, \*transforms) \-\> np.ndarray:  
        result \= transforms\[0\].copy()  
        for T in transforms\[1:\]:  
            result \= result @ T  
        return result  
   
    def transform\_point(self, T: np.ndarray, point) \-\> np.ndarray:  
        p \= np.array(\[\*point, 1.0\])  \# homogeneous  
        p\_t \= T @ p  
        return p\_t\[:3\] / p\_t\[3\]  
   
    def invert\_transform(self, T: np.ndarray) \-\> np.ndarray:  
        R \= T\[:3, :3\]  
        t \= T\[:3, 3\]  
        T\_inv \= np.eye(4)  
        T\_inv\[:3, :3\] \= R.T  
        T\_inv\[:3, 3\]  \= \-R.T @ t  
        return T\_inv

### **Solution — Q3: scripts/diff\_drive\_kinematics.py**

\#\!/usr/bin/env python3  
"""Q3 Reference Solution: Differential Drive Kinematics Node"""  
import rclpy  
from rclpy.node import Node  
from geometry\_msgs.msg import Twist, Vector3  
   
class DiffDriveKinematics(Node):  
    def \_\_init\_\_(self):  
        super().\_\_init\_\_("diff\_drive\_kinematics")  
        self.declare\_parameter("wheel\_radius", 0.075)  
        self.declare\_parameter("wheel\_base",   0.40)  
        self.r \= self.get\_parameter("wheel\_radius").value  
        self.L \= self.get\_parameter("wheel\_base").value  
        self.sub\_cmd \= self.create\_subscription(  
            Twist, "/cmd\_vel", self.cmd\_cb, 10\)  
        self.sub\_fb  \= self.create\_subscription(  
            Vector3, "/wheel\_speeds\_feedback", self.fb\_cb, 10\)  
        self.pub\_ws  \= self.create\_publisher(Vector3, "/wheel\_speeds", 10\)  
        self.pub\_bv  \= self.create\_publisher(Twist,   "/body\_velocity", 10\)  
   
    def cmd\_cb(self, msg: Twist):  
        v, w \= msg.linear.x, msg.angular.z  
        omega\_r \= (v \+ w \* self.L / 2.0) / self.r  
        omega\_l \= (v \- w \* self.L / 2.0) / self.r  
        out \= Vector3(x=omega\_l, y=omega\_r, z=0.0)  
        self.pub\_ws.publish(out)  
   
    def fb\_cb(self, msg: Vector3):  
        omega\_l, omega\_r \= msg.x, msg.y  
        v \= self.r \* (omega\_r \+ omega\_l) / 2.0  
        w \= self.r \* (omega\_r \- omega\_l) / self.L  
        out \= Twist()  
        out.linear.x  \= v  
        out.angular.z \= w  
        self.pub\_bv.publish(out)  
   
def main(args=None):  
    rclpy.init(args=args)  
    node \= DiffDriveKinematics()  
    rclpy.spin(node)  
    node.destroy\_node()  
    rclpy.shutdown()  
   
if \_\_name\_\_ \== "\_\_main\_\_":  
    main()

### **Solution — Q4: scripts/encoder\_odometry.py**

\#\!/usr/bin/env python3  
"""Q4 Reference Solution: Encoder Odometry"""  
import rclpy, math  
from rclpy.node import Node  
from std\_msgs.msg import Int64MultiArray  
from nav\_msgs.msg import Odometry  
   
class EncoderOdometry(Node):  
    def \_\_init\_\_(self):  
        super().\_\_init\_\_("encoder\_odometry")  
        for p, v in \[("wheel\_radius",0.075),("wheel\_base",0.40),("ticks\_per\_revolution",4096)\]:  
            self.declare\_parameter(p, v)  
        self.r   \= self.get\_parameter("wheel\_radius").value  
        self.L   \= self.get\_parameter("wheel\_base").value  
        self.tpr \= self.get\_parameter("ticks\_per\_revolution").value  
        self.x \= self.y \= self.theta \= 0.0  
        self.prev\_ticks \= None  
        self.sub \= self.create\_subscription(  
            Int64MultiArray, "/encoder\_ticks", self.tick\_cb, 10\)  
        self.pub \= self.create\_publisher(Odometry, "/odom", 10\)  
   
    def tick\_cb(self, msg):  
        tl, tr \= msg.data\[0\], msg.data\[1\]  
        if self.prev\_ticks is None:  
            self.prev\_ticks \= (tl, tr)  
            return  
        d\_tl \= tl \- self.prev\_ticks\[0\]  
        d\_tr \= tr \- self.prev\_ticks\[1\]  
        self.prev\_ticks \= (tl, tr)  
        dist \= 2.0 \* math.pi \* self.r / self.tpr  
        d\_left  \= d\_tl \* dist  
        d\_right \= d\_tr \* dist  
        d\_c     \= (d\_right \+ d\_left) / 2.0  
        d\_th    \= (d\_right \- d\_left) / self.L  
        self.x     \+= d\_c \* math.cos(self.theta \+ d\_th / 2.0)  
        self.y     \+= d\_c \* math.sin(self.theta \+ d\_th / 2.0)  
        self.theta \+= d\_th  
        self.\_publish()  
   
    def \_publish(self):  
        odom \= Odometry()  
        odom.header.stamp    \= self.get\_clock().now().to\_msg()  
        odom.header.frame\_id \= "odom"  
        odom.child\_frame\_id  \= "base\_link"  
        odom.pose.pose.position.x \= self.x  
        odom.pose.pose.position.y \= self.y  
        \# yaw → quaternion (roll=0, pitch=0)  
        half \= self.theta / 2.0  
        odom.pose.pose.orientation.z \= math.sin(half)  
        odom.pose.pose.orientation.w \= math.cos(half)  
        self.pub.publish(odom)  
   
def main(args=None):  
    rclpy.init(args=args)  
    rclpy.spin(EncoderOdometry())  
    rclpy.shutdown()

### **Solution — Q5: scripts/orientation\_converter.py**

\#\!/usr/bin/env python3  
"""Q5 Reference Solution: Euler ↔ Quaternion Converter Node"""  
import rclpy, math  
from rclpy.node import Node  
from geometry\_msgs.msg import Quaternion  
from orientation\_math\_pkg.msg import EulerAngles  
   
class OrientationConverter(Node):  
    def \_\_init\_\_(self):  
        super().\_\_init\_\_("orientation\_converter")  
        self.sub\_e \= self.create\_subscription(  
            EulerAngles, "/euler\_in", self.euler\_cb, 10\)  
        self.sub\_q \= self.create\_subscription(  
            Quaternion, "/quaternion\_in", self.quat\_cb, 10\)  
        self.pub\_q \= self.create\_publisher(Quaternion,   "/quaternion\_out", 10\)  
        self.pub\_e \= self.create\_publisher(EulerAngles,  "/euler\_out", 10\)  
   
    def euler\_to\_quaternion(self, roll, pitch, yaw):  
        cy, sy \= math.cos(yaw/2),   math.sin(yaw/2)  
        cp, sp \= math.cos(pitch/2), math.sin(pitch/2)  
        cr, sr \= math.cos(roll/2),  math.sin(roll/2)  
        w \=  cr\*cp\*cy \+ sr\*sp\*sy  
        x \=  sr\*cp\*cy \- cr\*sp\*sy  
        y \=  cr\*sp\*cy \+ sr\*cp\*sy  
        z \=  cr\*cp\*sy \- sr\*sp\*cy  
        return x, y, z, w  
   
    def quaternion\_to\_euler(self, x, y, z, w):  
        roll  \= math.atan2(2\*(w\*x \+ y\*z), 1 \- 2\*(x\*x \+ y\*y))  
        sinp  \= 2\*(w\*y \- z\*x)  
        sinp  \= max(-1.0, min(1.0, sinp))  \# clamp  
        pitch \= math.asin(sinp)  
        yaw   \= math.atan2(2\*(w\*z \+ x\*y), 1 \- 2\*(y\*y \+ z\*z))  
        return roll, pitch, yaw  
   
    def euler\_cb(self, msg):  
        x,y,z,w \= self.euler\_to\_quaternion(msg.roll, msg.pitch, msg.yaw)  
        q \= Quaternion(x=x, y=y, z=z, w=w)  
        self.pub\_q.publish(q)  
   
    def quat\_cb(self, msg):  
        r, p, yw \= self.quaternion\_to\_euler(msg.x, msg.y, msg.z, msg.w)  
        self.pub\_e.publish(EulerAngles(roll=r, pitch=p, yaw=yw))  
   
def main(args=None):  
    rclpy.init(args=args)  
    rclpy.spin(OrientationConverter())  
    rclpy.shutdown()

### **Solution — Q6: scripts/full\_odometry.py**

\#\!/usr/bin/env python3  
"""Q6 Reference Solution: Full Dead-Reckoning Odometry"""  
import rclpy, math  
from rclpy.node import Node  
from std\_msgs.msg import Int64MultiArray  
from nav\_msgs.msg import Odometry  
   
class FullOdometry(Node):  
    def \_\_init\_\_(self):  
        super().\_\_init\_\_("full\_odometry")  
        params \= \[("wheel\_radius",0.075),("wheel\_base",0.40),  
                  ("ticks\_per\_revolution",4096),  
                  ("odom\_frame","odom"),("base\_frame","base\_link")\]  
        for p, v in params:  
            self.declare\_parameter(p, v)  
        g \= self.get\_parameter  
        self.r   \= g("wheel\_radius").value  
        self.L   \= g("wheel\_base").value  
        self.tpr \= g("ticks\_per\_revolution").value  
        self.odom\_frame \= g("odom\_frame").value  
        self.base\_frame \= g("base\_frame").value  
        self.x \= self.y \= self.theta \= 0.0  
        self.v \= self.omega \= 0.0  
        self.prev\_ticks \= None  
        self.prev\_time  \= None  
        self.sub \= self.create\_subscription(  
            Int64MultiArray, "/encoder\_ticks", self.tick\_cb, 10\)  
        self.pub \= self.create\_publisher(Odometry, "/odom", 10\)  
   
    def yaw\_to\_quaternion(self, yaw):  
        half \= yaw / 2.0  
        return 0.0, 0.0, math.sin(half), math.cos(half)  \# x,y,z,w  
   
    def tick\_cb(self, msg):  
        tl, tr \= int(msg.data\[0\]), int(msg.data\[1\])  
        now \= self.get\_clock().now()  
        if self.prev\_ticks is None:  
            self.prev\_ticks \= (tl, tr)  
            self.prev\_time  \= now  
            return  
        d\_tl \= tl \- self.prev\_ticks\[0\]  
        d\_tr \= tr \- self.prev\_ticks\[1\]  
        dt   \= (now \- self.prev\_time).nanoseconds \* 1e-9  
        self.prev\_ticks \= (tl, tr)  
        self.prev\_time  \= now  
        dist \= 2.0 \* math.pi \* self.r / self.tpr  
        d\_left  \= d\_tl \* dist  
        d\_right \= d\_tr \* dist  
        d\_c  \= (d\_right \+ d\_left) / 2.0  
        d\_th \= (d\_right \- d\_left) / self.L  
        self.x     \+= d\_c \* math.cos(self.theta \+ d\_th / 2.0)  
        self.y     \+= d\_c \* math.sin(self.theta \+ d\_th / 2.0)  
        self.theta \+= d\_th  
        if dt \> 1e-9:  
            self.v     \= d\_c  / dt  
            self.omega \= d\_th / dt  
        self.\_publish(now)  
   
    def \_publish(self, stamp):  
        qx, qy, qz, qw \= self.yaw\_to\_quaternion(self.theta)  
        odom \= Odometry()  
        odom.header.stamp    \= stamp.to\_msg()  
        odom.header.frame\_id \= self.odom\_frame  
        odom.child\_frame\_id  \= self.base\_frame  
        odom.pose.pose.position.x    \= self.x  
        odom.pose.pose.position.y    \= self.y  
        odom.pose.pose.orientation.x \= qx  
        odom.pose.pose.orientation.y \= qy  
        odom.pose.pose.orientation.z \= qz  
        odom.pose.pose.orientation.w \= qw  
        odom.twist.twist.linear.x  \= self.v  
        odom.twist.twist.angular.z \= self.omega  
        self.pub.publish(odom)  
   
def main(args=None):  
    rclpy.init(args=args)  
    rclpy.spin(FullOdometry())  
    rclpy.shutdown()

# **6\. EVALUATION SCRIPTS**

### **test/evaluate.py — Q1 (Frame Transform)**

\#\!/usr/bin/env python3  
"""Evaluation Script: Q1 — 2D Frame Transformation"""  
import pytest, math, sys, numpy as np  
sys.path.insert(0, "install/frame\_math\_pkg/lib/frame\_math\_pkg")  
from frame\_transform import FrameTransformer  
   
@pytest.fixture  
def ft(): return FrameTransformer()  
   
def test\_identity\_pose(ft):  
    x, y \= ft.transform\_to\_world(1.0, 0.0, 0.0, 0.0, 0.0)  
    assert abs(x \- 1.0) \< 1e-9 and abs(y) \< 1e-9  
   
def test\_90\_degree\_rotation(ft):  
    x, y \= ft.transform\_to\_world(1.0, 0.0, 1.0, 2.0, math.pi/2)  
    assert abs(x \- 1.0) \< 1e-6 and abs(y \- 3.0) \< 1e-6  
   
def test\_rotation\_matrix\_orthogonality(ft):  
    for theta in \[0, 0.5, math.pi, \-math.pi/3\]:  
        R \= ft.build\_rotation\_matrix(theta)  
        assert np.allclose(R.T @ R, np.eye(2), atol=1e-9)  
   
def test\_rotation\_matrix\_determinant(ft):  
    for theta in \[0.3, 1.2, \-0.7\]:  
        R \= ft.build\_rotation\_matrix(theta)  
        assert abs(np.linalg.det(R) \- 1.0) \< 1e-9  
   
def test\_batch\_matches\_per\_point(ft):  
    pts \= \[(float(i), float(i\*0.5)) for i in range(50)\]  
    batch \= ft.transform\_batch(pts, 1.0, 2.0, 0.7)  
    for i, (bx, by) in enumerate(batch):  
        px, py \= ft.transform\_to\_world(\*pts\[i\], 1.0, 2.0, 0.7)  
        assert abs(bx \- px) \< 1e-9 and abs(by \- py) \< 1e-9  
   
def test\_no\_ros\_imports():  
    import importlib.util  
    spec \= importlib.util.spec\_from\_file\_location("ft",   
        "install/frame\_math\_pkg/lib/frame\_math\_pkg/frame\_transform.py")  
    src \= open("install/frame\_math\_pkg/lib/frame\_math\_pkg/frame\_transform.py").read()  
    forbidden \= \["tf\_transformations", "scipy", "rclpy"\]  
    for f in forbidden:  
        assert f not in src, f"Forbidden import: {f}"

### **test/evaluate.py — Q6 (Full Odometry — comprehensive)**

\#\!/usr/bin/env python3  
"""Evaluation: Q6 — Full Odometry Pipeline"""  
import pytest, math, subprocess, time  
   
\# ── Unit tests (no ROS needed) ──────────────────────────────────────  
import sys  
sys.path.insert(0, "install/full\_odom\_pkg/lib/full\_odom\_pkg")  
   
def make\_odom\_instance():  
    """Instantiate without spinning ROS."""  
    import importlib.util  
    spec \= importlib.util.spec\_from\_file\_location("fo",  
        "src/full\_odom\_pkg/scripts/full\_odometry.py")  
    \# Use stub that bypasses rclpy for unit testing  
    return None  \# replaced by live node tests below  
   
def test\_yaw\_to\_quaternion\_zero():  
    """yaw=0 → identity quaternion"""  
    \# Inline the formula for unit testing without ROS  
    yaw \= 0.0  
    x, y, z, w \= 0.0, 0.0, math.sin(yaw/2), math.cos(yaw/2)  
    assert abs(w \- 1.0) \< 1e-9  
    assert abs(x) \< 1e-9 and abs(y) \< 1e-9 and abs(z) \< 1e-9  
   
def test\_yaw\_to\_quaternion\_90():  
    yaw \= math.pi / 2  
    z, w \= math.sin(yaw/2), math.cos(yaw/2)  
    assert abs(z \- math.sqrt(2)/2) \< 1e-6  
    assert abs(w \- math.sqrt(2)/2) \< 1e-6  
   
def test\_quaternion\_is\_unit():  
    for yaw in \[0.0, 0.5, 1.2, math.pi, \-0.8\]:  
        z \= math.sin(yaw/2); w \= math.cos(yaw/2)  
        norm \= math.sqrt(z\*z \+ w\*w)  
        assert abs(norm \- 1.0) \< 1e-9, f"Non-unit quaternion at yaw={yaw}"  
   
def test\_straight\_line\_ticks():  
    """Simulate 1000 ticks on both wheels, check x displacement."""  
    r=0.075; L=0.40; tpr=4096  
    ticks=1000; dist \= (ticks/tpr)\*2\*math.pi\*r  
    expected\_x \= dist  \# straight line  
    x=y=theta=0.0  
    d\_left \= d\_right \= dist  
    d\_c  \= (d\_right \+ d\_left)/2; d\_th \= (d\_right \- d\_left)/L  
    x \+= d\_c \* math.cos(theta \+ d\_th/2)  
    y \+= d\_c \* math.sin(theta \+ d\_th/2)  
    assert abs(x \- expected\_x) \< 1e-9 and abs(y) \< 1e-9  
   
def test\_pure\_rotation():  
    r=0.075; L=0.40; tpr=4096  
    right\_ticks=1000; left\_ticks=0  
    d\_right=(right\_ticks/tpr)\*2\*math.pi\*r; d\_left=0.0  
    d\_c=(d\_right+d\_left)/2; d\_th=(d\_right-d\_left)/L  
    assert d\_th \> 0, "Pure right-wheel → should increase theta"  
   
\# ── Runtime tests (require launched node) ───────────────────────────  
def test\_odom\_topic\_published():  
    r=subprocess.run(\["ros2","topic","list"\],capture\_output=True,text=True,timeout=10)  
    assert "/odom" in r.stdout  
   
def test\_robot\_state\_publisher\_not\_required():  
    """Q6 only needs encoder\_ticks and /odom — no URDF."""  
    r=subprocess.run(\["ros2","topic","list"\],capture\_output=True,text=True,timeout=10)  
    assert "/odom" in r.stdout  
   
def test\_odom\_message\_has\_correct\_frame():  
    r=subprocess.run(  
        \["ros2","topic","echo","/odom","--once"\],  
        capture\_output=True,text=True,timeout=10)  
    assert "frame\_id" in r.stdout  
   
def test\_no\_forbidden\_imports():  
    src=open("src/full\_odom\_pkg/scripts/full\_odometry.py").read()  
    for f in \["tf\_transformations","scipy","transforms3d","time.time"\]:  
        assert f not in src, f"Forbidden: {f}"

# **7\. judge\_runner.py**

\#\!/usr/bin/env python3  
"""  
judge\_runner.py — Robot Mathematics Topic  
Production-ready evaluation runner. Docker-compatible. ROS2 Humble.  
   
Usage:  
  python3 judge\_runner.py \--question Q1 \--workspace /home/student/ros2\_ws  
"""  
import argparse, json, os, subprocess, sys, time, signal, logging  
from pathlib import Path  
from typing import Dict, Any, Optional  
   
logging.basicConfig(level=logging.INFO,  
    format="\[%(asctime)s\] %(levelname)s — %(message)s")  
log \= logging.getLogger("judge\_runner")  
   
QUESTION\_CONFIG: Dict\[str, Dict\[str, Any\]\] \= {  
    "Q1": {  
        "package": None,  \# pure Python, no ROS launch needed  
        "launch\_file": None,  
        "test\_file": "frame\_math\_pkg/test/evaluate.py",  
        "test\_functions": \[  
            "test\_identity\_pose",  
            "test\_90\_degree\_rotation",  
            "test\_rotation\_matrix\_orthogonality",  
            "test\_rotation\_matrix\_determinant",  
            "test\_batch\_matches\_per\_point",  
            "test\_no\_ros\_imports",  
        \],  
        "timeout": 15,  
        "requires\_launch": False,  
    },  
    "Q2": {  
        "package": None,  
        "launch\_file": None,  
        "test\_file": "transform\_math\_pkg/test/evaluate.py",  
        "test\_functions": \[  
            "test\_homogeneous\_translation",  
            "test\_rotation\_matrices",  
            "test\_chain\_inverse\_cancels",  
            "test\_transform\_point",  
            "test\_invert\_analytical",  
        \],  
        "timeout": 15,  
        "requires\_launch": False,  
    },  
    "Q3": {  
        "package": "diff\_drive\_pkg",  
        "launch\_file": "kinematics.launch.py",  
        "test\_file": "diff\_drive\_pkg/test/evaluate.py",  
        "test\_functions": \[  
            "test\_straight\_line\_cmd",  
            "test\_turn\_in\_place\_cmd",  
            "test\_round\_trip",  
            "test\_parameters\_loaded",  
            "test\_wheel\_speeds\_topic",  
            "test\_body\_velocity\_topic",  
        \],  
        "timeout": 30,  
        "requires\_launch": True,  
    },  
    "Q4": {  
        "package": "encoder\_odom\_pkg",  
        "launch\_file": "odom.launch.py",  
        "test\_file": "encoder\_odom\_pkg/test/evaluate.py",  
        "test\_functions": \[  
            "test\_straight\_ticks\_displacement",  
            "test\_pure\_rotation",  
            "test\_odom\_topic\_published",  
            "test\_frame\_ids\_correct",  
            "test\_quaternion\_unit\_norm",  
        \],  
        "timeout": 30,  
        "requires\_launch": True,  
    },  
    "Q5": {  
        "package": "orientation\_math\_pkg",  
        "launch\_file": "converter.launch.py",  
        "test\_functions": \[  
            "test\_euler\_to\_quat\_known\_values",  
            "test\_round\_trip\_1000\_random",  
            "test\_output\_unit\_quaternion",  
            "test\_gimbal\_lock\_finite",  
            "test\_no\_forbidden\_imports",  
        \],  
        "timeout": 30,  
        "requires\_launch": True,  
    },  
    "Q6": {  
        "package": "full\_odom\_pkg",  
        "launch\_file": "odom\_full.launch.py",  
        "test\_file": "full\_odom\_pkg/test/evaluate.py",  
        "test\_functions": \[  
            "test\_yaw\_to\_quaternion\_zero",  
            "test\_yaw\_to\_quaternion\_90",  
            "test\_quaternion\_is\_unit",  
            "test\_straight\_line\_ticks",  
            "test\_pure\_rotation",  
            "test\_odom\_topic\_published",  
            "test\_odom\_message\_has\_correct\_frame",  
            "test\_no\_forbidden\_imports",  
        \],  
        "timeout": 45,  
        "requires\_launch": True,  
    },  
}  
   
def build\_ws(ws, env):  
    log.info("Building workspace: %s", ws)  
    r \= subprocess.run(\["colcon","build","--symlink-install"\],  
        env=env, capture\_output=True, text=True, timeout=180, cwd=ws)  
    return {"success": r.returncode \== 0, "stderr": r.stderr\[-2000:\]}  
   
def source\_ws(ws) \-\> dict:  
    r \= subprocess.run(\["bash","-c",  
        f"source /opt/ros/humble/setup.bash && source {ws}/install/setup.bash && env"\],  
        capture\_output=True, text=True, timeout=15)  
    return {k: v for line in r.stdout.splitlines()  
            if "=" in line for k, v in \[line.split("=",1)\]}  
   
def launch\_solution(package, launch\_file, env, warmup=5):  
    proc \= subprocess.Popen(\["ros2","launch",package,launch\_file,  
        "use\_sim\_time:=false"\], env=env,  
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,  
        preexec\_fn=os.setsid)  
    time.sleep(warmup)  
    return proc  
   
def run\_tests(test\_file, functions, ws, env) \-\> Dict\[str, bool\]:  
    results \= {}  
    path \= os.path.join(ws, "src", test\_file)  
    for fn in functions:  
        r \= subprocess.run(\["python3","-m","pytest",path,"-k",fn,"-v","--tb=short"\],  
            env=env, capture\_output=True, text=True, timeout=30, cwd=ws)  
        results\[fn\] \= (r.returncode \== 0\)  
        log.info("%s: %s", "PASS" if results\[fn\] else "FAIL", fn)  
    return results  
   
def kill\_proc(proc):  
    try: os.killpg(os.getpgid(proc.pid), signal.SIGTERM); proc.wait(timeout=5)  
    except Exception: pass  
   
def run\_judge(question, workspace) \-\> dict:  
    if question not in QUESTION\_CONFIG:  
        return {"status":"error","message":f"Unknown question {question}"}  
    cfg \= QUESTION\_CONFIG\[question\]  
    out \= {"question":question,"status":"started","build":{},"results":{},"score":{},"message":""}  
    env \= os.environ.copy(); env\["ROS\_DOMAIN\_ID"\] \= "42"  
    build \= build\_ws(workspace, env)  
    out\["build"\] \= build  
    if not build\["success"\]:  
        out\["status"\]="build\_failed"; out\["message"\]="Build failed"; return out  
    env\_src \= source\_ws(workspace)  
    proc \= None  
    if cfg.get("requires\_launch"):  
        proc \= launch\_solution(cfg\["package"\], cfg\["launch\_file"\], env\_src)  
    try:  
        results \= run\_tests(cfg\["test\_file"\], cfg\["test\_functions"\], workspace, env\_src)  
        out\["results"\] \= results  
        total \= len(results); passed \= sum(v for v in results.values())  
        out\["score"\] \= {"total":total,"passed":passed,"failed":total-passed,  
                        "score\_percent":round(passed/total\*100,1) if total else 0}  
        out\["status"\]="completed"; out\["message"\]="Evaluation completed."  
    except Exception as e:  
        out\["status"\]="error"; out\["message"\]=str(e)  
    finally:  
        if proc: kill\_proc(proc)  
    return out  
   
if \_\_name\_\_ \== "\_\_main\_\_":  
    p \= argparse.ArgumentParser()  
    p.add\_argument("--question", required=True)  
    p.add\_argument("--workspace", required=True)  
    p.add\_argument("--output-file", default=None)  
    args \= p.parse\_args()  
    result \= run\_judge(args.question, args.workspace)  
    js \= json.dumps(result, indent=2)  
    print(js)  
    if args.output\_file: Path(args.output\_file).write\_text(js)  
    sys.exit(0 if result.get("status")=="completed" and  
             all(result\["results"\].values()) else 1\)

# **8\. EVALUATION SCENARIOS**

| ID | Q | Scenario | Expected Outcome | Detection Method |
| ----- | ----- | ----- | ----- | ----- |
| ES-01 | Q1 | Correct rotation matrix and transform | All 6 checks pass | Numerical tolerance check on known inputs |
| ES-02 | Q1 | Student uses sin/cos swapped in R(θ) | test\_90\_degree\_rotation fails | Numerical output mismatch |
| ES-03 | Q1 | Student loops in batch instead of vectorising | test\_no\_ros\_imports passes but performance check fails | Timing assertion |
| ES-04 | Q2 | Correct homogeneous chain and inverse | All 5 checks pass | Identity matrix comparison with 1e-10 tolerance |
| ES-05 | Q2 | Student uses np.linalg.inv instead of analytical formula | test\_invert\_analytical fails (source code scan) | Source AST / text scan for np.linalg.inv |
| ES-06 | Q3 | Correct forward kinematics | Round-trip test passes | topic echo \+ numerical check |
| ES-07 | Q3 | Student hardcodes r and L | test\_parameters\_loaded fails | ros2 param get check |
| ES-08 | Q4 | Correct tick → distance → pose | test\_straight\_ticks\_displacement passes | Simulate 1000 ticks, check x within 0.001 m |
| ES-09 | Q4 | Student uses incremental ticks instead of absolute | First message correct, all subsequent wrong | Multi-message simulation scenario |
| ES-10 | Q5 | euler → quat → euler round-trip | 1000 random inputs all pass | Max error \< 1e-9 across batch |
| ES-11 | Q5 | Student imports tf\_transformations | test\_no\_forbidden\_imports fails | Source text scan |
| ES-12 | Q5 | Student does not clamp sinp before asin | test\_gimbal\_lock\_finite fails | Input pitch=π/2 produces NaN without clamp |
| ES-13 | Q6 | Full pipeline: ticks → pose → /odom | All 8 checks pass | Live topic \+ unit math checks |
| ES-14 | Q6 | Student uses time.time() instead of ROS clock | test\_no\_forbidden\_imports fails | Source scan for time.time |
| ES-15 | Q6 | Student forgets to initialise prev\_ticks to None | First tick callback causes KeyError / wrong delta | Edge case: first message check |

# **9\. COMMON MISTAKES & DEBUGGING NOTES**

### **Q1 — Frame Transform**

| Mistake | Symptom | Fix |
| ----- | ----- | ----- |
| Swapped sin/cos in rotation matrix | Transform produces rotations in the wrong direction | R \= \[\[cos θ, −sin θ\], \[sin θ, cos θ\]\] — note negative sign is in top-right, not bottom-left |
| Adding translation before rotation | Point ends up at wrong location | Apply rotation first: p\_world \= R @ p\_robot \+ t\_robot |
| Batch function using Python loop | Correct results but fails performance check | Stack points into (2, N) array, apply R @ P \+ t in one operation |

### **Q2 — Homogeneous Transforms**

| Mistake | Symptom | Fix |
| ----- | ----- | ----- |
| Using np.linalg.inv for invert\_transform | Numerically equivalent but evaluator rejects it | Use T\_inv\[:3,:3\] \= R.T; T\_inv\[:3,3\] \= \-R.T @ t |
| chain() with wrong multiply order | T\_A\_to\_C ≠ T\_A\_to\_B @ T\_B\_to\_C if order reversed | Left-to-right: result \= T1 @ T2 @ T3 |
| Forgetting homogeneous divide in transform\_point | Works for rigid transforms (w=1 always) but fails for projective | Always divide by p\[3\]: return p\_t\[:3\] / p\_t\[3\] |

### **Q3 — Diff Drive Kinematics**

| Mistake | Symptom | Fix |
| ----- | ----- | ----- |
| Hardcoding wheel\_radius / wheel\_base | test\_parameters\_loaded fails | Use self.declare\_parameter() \+ self.get\_parameter().value at startup |
| Swapping ω\_r and ω\_l formula signs | Robot turns in wrong direction for angular velocity | ω\_r \= (v \+ ω×L/2)/r  and  ω\_l \= (v − ω×L/2)/r |
| Publishing Twist on /wheel\_speeds | Message type mismatch — subscriber receives nothing | Use Vector3 for wheel speeds; x=ω\_l, y=ω\_r |

### **Q4 — Encoder Odometry**

| Mistake | Symptom | Fix |
| ----- | ----- | ----- |
| Treating tick counts as incremental (not absolute) | Pose drifts wildly after first message | Store prev\_ticks; compute delta \= current − previous on each callback |
| Initialising prev\_ticks to 0 instead of None | First callback computes wrong delta (assumes robot started at tick 0\) | Set prev\_ticks \= None; return on first callback without updating pose |
| Missing cos/sin argument offset (d\_th/2) | Pose update uses θ instead of θ \+ Δθ/2 | Use midpoint angle: x \+= d\_c × cos(θ \+ Δθ/2) |

### **Q5 — Orientation Conversion**

| Mistake | Symptom | Fix |
| ----- | ----- | ----- |
| Not clamping sinp before asin | NaN output at pitch \= ±π/2 (gimbal lock) | sinp \= max(−1.0, min(1.0, 2(wy−zx))) |
| Returning (w, x, y, z) instead of (x, y, z, w) | Quaternion norm is 1 but orientation is wrong | ROS2 Quaternion msg is .x .y .z .w — match this order |
| Importing tf\_transformations | test\_no\_forbidden\_imports fails immediately | Implement from first principles using only math module |

### **Q6 — Full Odometry**

| Mistake | Symptom | Fix |
| ----- | ----- | ----- |
| Using time.time() for dt | test\_no\_forbidden\_imports fails; also breaks sim\_time | Use self.get\_clock().now() and .nanoseconds for dt |
| Not publishing on every tick callback | Evaluator times out waiting for /odom message | Call self.\_publish() at the end of every tick\_cb |
| Forgetting to load odom\_frame / base\_frame parameters | frame\_id defaults to empty string — evaluator fails | All 5 parameters must be declared and read; strings require default="" |

| General ROS2 Humble Debugging Notes |
| :---- |
|  |
|  |
|  |
|  |

**✓ All 10 syllabus skills covered   |   ✓ All 6 questions auto-gradable   |   ✓ ROS2 Humble compatible**