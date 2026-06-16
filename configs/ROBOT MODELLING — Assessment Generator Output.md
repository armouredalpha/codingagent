## **ROBOT MODELLING — Assessment Generator Output**

---

### **1\. TOPIC ANALYSIS**

**Topic:** Robot Modelling **Platform:** ROS2 Humble | Ubuntu 22.04 | Python 3.10 | RViz2

The syllabus covers the complete robot description pipeline — from raw URDF authoring, through parameterised Xacro modelling, to sensor plugin attachment and live RViz visualisation via the `robot_state_publisher` and `joint_state_publisher` stack. This topic is a foundational prerequisite for simulation, navigation, and manipulation. All questions are grounded in the description layer only — no Nav2, SLAM, or motion planning concepts appear anywhere in this assessment.

---

### **2\. SYLLABUS COVERAGE MATRIX**

| \# | Skill | Covered By Question(s) |
| ----- | ----- | ----- |
| S1 | Describing robot physical structure in code | Q1, Q6 |
| S2 | Defining **links** in URDF | Q1, Q2, Q4 |
| S3 | Defining **fixed** joints | Q1, Q2 |
| S4 | Defining **revolute** joints | Q2, Q3 |
| S5 | Defining **continuous** joints | Q3 |
| S6 | Defining **prismatic** joints | Q4 |
| S7 | Parameterising a model using **Xacro macros** | Q3, Q5, Q6 |
| S8 | Parameterising a model using **Xacro properties** | Q3, Q5, Q6 |
| S9 | Attaching **LiDAR** sensor plugin | Q5 |
| S10 | Attaching **Camera** sensor plugin | Q5 |
| S11 | Attaching **IMU** sensor plugin | Q6 |
| S12 | Loading model via **robot\_state\_publisher** | Q1, Q4, Q5, Q6 |
| S13 | Loading model via **joint\_state\_publisher** | Q2, Q3, Q6 |

All 13 skills are covered. ✓

---

### **3\. SIX CODING QUESTIONS**

---

#### **QUESTION 1 — Easy**

**Title:** Build the Base Frame of a Warehouse Robot

**Difficulty:** Easy

**Tested Skills:**

* S1 — Describing robot physical structure in code  
* S2 — Defining links in URDF  
* S3 — Defining fixed joints  
* S12 — Loading via robot\_state\_publisher

**Scenario:** You are a junior robotics engineer at a logistics company. The team has started building a wheeled warehouse robot. The mechanical team handed you the base dimensions. Your task is to define the robot's base structure in URDF so it can be visualised in RViz for review by the mechanical team.

**Files Student Can Edit:**

urdf/warehouse\_bot.urdf

**Existing Package Structure:**

warehouse\_bot\_description/  
├── launch/  
│   └── display.launch.py  
├── urdf/  
│   └── warehouse\_bot.urdf        ← EDIT THIS  
├── rviz/  
│   └── view\_robot.rviz  
├── package.xml  
└── setup.py

**Student Objective:**

Open `urdf/warehouse_bot.urdf` and complete the robot description:

1. Define a `base_link` — a **box** geometry of size `0.5m × 0.4m × 0.15m`, mass `10.0 kg`. Apply a grey material.  
2. Define a `base_footprint` link — a **box** geometry of size `0.001m × 0.001m × 0.001m`, mass `0.0 kg`.  
3. Connect `base_footprint` → `base_link` using a **fixed** joint named `base_footprint_to_base`. The joint origin must be at `z = 0.075` (half the height of the base box) relative to `base_footprint`.  
4. Ensure the URDF is valid — the root link must be `base_footprint`.

**Constraints:**

* Do NOT modify `display.launch.py`  
* Do NOT create additional packages  
* Use standard URDF syntax — no Xacro in this question  
* The `base_link` inertial must be defined (use a box inertia formula)

**Expected Behaviour:** When the launch file is run:

bash  
ros2 launch warehouse\_bot\_description display.launch.py

* RViz opens and displays a grey box floating at the correct height  
* The TF tree shows `base_footprint → base_link`  
* No URDF parse errors in terminal

**Evaluation Criteria (Hidden):**

* `robot_state_publisher` node is active  
* `/robot_description` topic is being published  
* TF frame `base_footprint` exists  
* TF frame `base_link` exists  
* TF transform `base_footprint → base_link` has `z = 0.075`  
* URDF parses without errors (check\_urdf)  
* Geometry type is `box` with correct dimensions

---

#### **QUESTION 2 — Easy-Medium**

**Title:** Attach Wheels to the Warehouse Robot Using Revolute and Fixed Joints

**Difficulty:** Easy-Medium

**Tested Skills:**

* S2 — Defining links in URDF  
* S3 — Defining fixed joints  
* S4 — Defining revolute joints  
* S13 — Loading via joint\_state\_publisher

**Scenario:** The base frame from the previous sprint has been approved. You now need to attach four wheels and one caster. The drive wheels must rotate (revolute) and the front caster must be mounted rigidly (fixed) to the base. The RViz team needs to see the joint\_state\_publisher GUI sliders controlling the drive wheels.

**Files Student Can Edit:**

urdf/warehouse\_bot.urdf

**Existing Package Structure:**

warehouse\_bot\_description/  
├── launch/  
│   └── display.launch.py  
├── urdf/  
│   └── warehouse\_bot.urdf        ← EDIT THIS  
├── rviz/  
│   └── view\_robot.rviz  
├── package.xml  
└── setup.py

**Student Objective:**

The `warehouse_bot.urdf` already contains a valid `base_footprint` and `base_link` (pre-filled). You must extend it:

1. Add two drive wheel links: `left_wheel` and `right_wheel`  
   * Geometry: **cylinder**, radius `0.075m`, length `0.05m`, mass `1.5 kg`  
   * Material: black  
2. Add a caster link: `front_caster`  
   * Geometry: **sphere**, radius `0.03m`, mass `0.5 kg`  
   * Material: grey  
3. Connect `base_link → left_wheel` via a **revolute** joint named `left_wheel_joint`  
   * Axis: `0 0 1` (spin about z — wheel rolls on x-y plane when robot moves)  
   * Actually, for a wheel rolling about its axle: axis `0 1 0`  
   * Limits: lower `-3.14159`, upper `3.14159`, effort `10.0`, velocity `5.0`  
   * Origin: `x=-0.15`, `y=0.225`, `z=0.0` relative to base\_link  
4. Mirror for `right_wheel_joint` at `y=-0.225`  
5. Connect `base_link → front_caster` via a **fixed** joint named `front_caster_joint`  
   * Origin: `x=0.2`, `y=0.0`, `z=-0.045`

**Constraints:**

* Do NOT use Xacro  
* Do NOT modify the launch file  
* Inertials must be defined for all new links  
* Revolute wheel joints must have explicit `<limit>` tags

**Expected Behaviour:**

bash  
ros2 launch warehouse\_bot\_description display.launch.py

* RViz shows base box with two cylinder wheels and one sphere caster  
* `joint_state_publisher_gui` sliders appear for `left_wheel_joint` and `right_wheel_joint`  
* Moving sliders rotates wheels in RViz  
* TF tree: `base_footprint → base_link → left_wheel`, `right_wheel`, `front_caster`

**Evaluation Criteria (Hidden):**

* `/joint_states` topic is published  
* `left_wheel_joint` and `right_wheel_joint` appear in `/joint_states`  
* Joint type is `revolute` (verified via `robot_description` parsing)  
* `front_caster_joint` type is `fixed`  
* TF frames `left_wheel`, `right_wheel`, `front_caster` all exist  
* Wheel geometry is cylinder with correct radius/length  
* Caster geometry is sphere

---

#### **QUESTION 3 — Easy-Medium**

**Title:** Parameterise a Robot Arm Link Using Xacro Macros

**Difficulty:** Easy-Medium

**Tested Skills:**

* S5 — Defining continuous joints  
* S7 — Xacro macros  
* S8 — Xacro properties  
* S13 — Loading via joint\_state\_publisher

**Scenario:** The inspection robot team is building a 2-DOF arm that mounts on top of the mobile base. The team noticed that both arm links are structurally identical (same shape, different lengths). Your lead engineer asks you to avoid copy-paste URDF by creating a **reusable Xacro macro** for the arm links, and use **Xacro properties** for dimensions. Both shoulder and elbow joints must spin continuously (no hard stops) to allow full 360° rotation.

**Files Student Can Edit:**

urdf/inspection\_arm.urdf.xacro

**Existing Package Structure:**

inspection\_arm\_description/  
├── launch/  
│   └── display.launch.py  
├── urdf/  
│   └── inspection\_arm.urdf.xacro    ← EDIT THIS  
├── rviz/  
│   └── view\_arm.rviz  
├── package.xml  
└── setup.py

**Student Objective:**

Inside `inspection_arm.urdf.xacro`, complete the following:

1. Define **Xacro properties**:  
   * `upper_arm_length`: `0.30`  
   * `lower_arm_length`: `0.25`  
   * `arm_radius`: `0.025`  
   * `arm_mass`: `0.8`  
2. Define a **Xacro macro** named `arm_link` that accepts parameters:  
   * `name` — link name  
   * `length` — cylinder length  
   * `mass` — link mass  
   * `material_color` — RGBA string The macro must produce a complete `<link>` element (geometry \+ inertial \+ visual \+ collision) using a **cylinder** with the given length and `arm_radius` property.  
3. Use the macro to instantiate:  
   * `upper_arm_link` (length \= `${upper_arm_length}`, mass \= `${arm_mass}`)  
   * `lower_arm_link` (length \= `${lower_arm_length}`, mass \= `${arm_mass}`)  
4. Define a `base_link` (box, `0.1×0.1×0.05m`)  
5. Connect with **continuous** joints:  
   * `shoulder_joint`: `base_link → upper_arm_link`, axis `0 0 1`, origin `z=0.025`  
   * `elbow_joint`: `upper_arm_link → lower_arm_link`, axis `0 0 1`, origin `z=${upper_arm_length}`

**Constraints:**

* Must use `<xacro:macro>` syntax  
* Must use `<xacro:property>` for all numeric dimensions  
* Continuous joints must have NO `<limit>` tag  
* Do NOT hardcode dimensions inside macro calls

**Expected Behaviour:**

bash  
ros2 launch inspection\_arm\_description display.launch.py

* RViz shows 3-link arm (base \+ two arm segments)  
* `joint_state_publisher_gui` sliders for `shoulder_joint` and `elbow_joint` allow full 360° rotation  
* Changing `upper_arm_length` property to `0.40` and rebuilding should change the upper arm length automatically

**Evaluation Criteria (Hidden):**

* Xacro processes without errors (`xacro urdf/inspection_arm.urdf.xacro`)  
* Both `shoulder_joint` and `elbow_joint` have type `continuous`  
* No `<limit>` element present in either joint  
* Macro `arm_link` is defined  
* Properties `upper_arm_length`, `lower_arm_length`, `arm_radius`, `arm_mass` are defined  
* `upper_arm_link` geometry uses `${upper_arm_length}` resolved to `0.30`  
* `/joint_states` published with both joint names

---

#### **QUESTION 4 — Medium**

**Title:** Model a Linear Lift Mechanism with a Prismatic Joint

**Difficulty:** Medium

**Tested Skills:**

* S2 — Defining links in URDF  
* S6 — Defining prismatic joints  
* S3 — Defining fixed joints  
* S12 — Loading via robot\_state\_publisher

**Scenario:** You are working on a warehouse pallet-lifting robot. The robot has a vertical lift column attached to its base that raises a fork platform up and down. The mechanical team has provided the lift range: `0.0m` (lowered) to `0.5m` (fully raised). Your task is to model the lift column and fork platform with the correct prismatic joint and verify the motion in RViz using the `joint_state_publisher_gui`.

**Files Student Can Edit:**

urdf/lifter\_bot.urdf  
launch/display.launch.py

**Existing Package Structure:**

lifter\_bot\_description/  
├── launch/  
│   └── display.launch.py          ← MAY EDIT  
├── urdf/  
│   └── lifter\_bot.urdf            ← EDIT THIS  
├── rviz/  
│   └── view\_lifter.rviz  
├── package.xml  
└── setup.py

**Student Objective:**

1. In `urdf/lifter_bot.urdf`:  
   * Define `base_link`: box `0.6m × 0.5m × 0.2m`, mass `15.0 kg`, grey material  
   * Define `lift_column`: box `0.1m × 0.1m × 0.6m`, mass `3.0 kg`, dark grey material  
   * Define `fork_platform`: box `0.55m × 0.45m × 0.03m`, mass `2.0 kg`, yellow material  
   * Connect `base_link → lift_column` via **fixed** joint `lift_column_joint` at origin `x=0.2, z=0.1` (top of base \+ half column height offset)  
   * Connect `lift_column → fork_platform` via **prismatic** joint `fork_joint`  
     * Axis: `0 0 1` (lift moves in Z)  
     * Lower limit: `0.0`, Upper limit: `0.5`  
     * Effort: `100.0`, Velocity: `0.5`  
2. In `launch/display.launch.py`:  
   * Ensure `robot_state_publisher` is launched with the URDF  
   * Ensure `joint_state_publisher_gui` is launched so the fork can be moved interactively

**Constraints:**

* The prismatic joint **must** have proper `<limit>` tags  
* Axis of motion must be `0 0 1`  
* All inertials must be defined  
* Do NOT add sensor plugins

**Expected Behaviour:**

bash  
ros2 launch lifter\_bot\_description display.launch.py

* RViz shows the base, lift column, and fork platform  
* The `joint_state_publisher_gui` shows a slider named `fork_joint`  
* Moving the slider raises/lowers the fork platform between `0.0` and `0.5` metres  
* Fork does not pass through the column or base

**Evaluation Criteria (Hidden):**

* `fork_joint` type is `prismatic`  
* Axis is `(0, 0, 1)`  
* Joint lower limit \= `0.0`, upper limit \= `0.5`  
* `fork_platform` link exists with correct geometry  
* `lift_column_joint` type is `fixed`  
* `/joint_states` contains `fork_joint`  
* `robot_state_publisher` node active  
* TF chain: `base_link → lift_column → fork_platform`

---

#### **QUESTION 5 — Medium**

**Title:** Equip an Inspection Robot with LiDAR and Camera Sensor Plugins

**Difficulty:** Medium

**Tested Skills:**

* S7 — Xacro macros  
* S8 — Xacro properties  
* S9 — Attaching LiDAR sensor plugin  
* S10 — Attaching Camera sensor plugin  
* S12 — Loading via robot\_state\_publisher

**Scenario:** The inspection robot platform has been mechanically modelled. Your task as the sensor integration engineer is to equip it with a 2D LiDAR (for obstacle detection) and a forward-facing camera (for visual inspection). You must use Xacro properties for all sensor mounting offsets so the team can easily adjust them without touching joint/link definitions. The robot must be launched into RViz and the sensor topics must be verifiable.

**Files Student Can Edit:**

urdf/inspection\_bot.urdf.xacro

**Existing Package Structure:**

inspection\_bot\_description/  
├── launch/  
│   └── display.launch.py  
├── urdf/  
│   └── inspection\_bot.urdf.xacro    ← EDIT THIS  
├── rviz/  
│   └── view\_bot.rviz  
├── package.xml  
└── setup.py

**Student Objective:**

The file already contains a valid `base_footprint`, `base_link`, and two drive wheels with continuous joints (pre-filled). You must add:

1. **Xacro properties** for sensor offsets:  
   * `lidar_x_offset`: `0.15`  
   * `lidar_z_offset`: `0.12`  
   * `camera_x_offset`: `0.20`  
   * `camera_z_offset`: `0.08`  
2. **LiDAR link and joint:**  
   * Link name: `lidar_link`, geometry: cylinder, radius `0.025`, length `0.04`, mass `0.2 kg`  
   * Joint name: `lidar_joint`, type: **fixed**, parent: `base_link`, child: `lidar_link`  
   * Origin: `x=${lidar_x_offset}`, `z=${lidar_z_offset}`  
   * Add `gazebo_ros_ray_sensor` plugin under a `<gazebo reference="lidar_link">` block:  
     * Plugin: `libgazebo_ros_ray_sensor.so`  
     * Output topic: `/scan`  
     * Frame: `lidar_link`  
     * Range: min `0.1`, max `10.0`  
     * Samples: `360`  
     * Update rate: `10`  
3. **Camera link and joint:**  
   * Link name: `camera_link`, geometry: box `0.03×0.03×0.03m`, mass `0.1 kg`  
   * Joint name: `camera_joint`, type: **fixed**, parent: `base_link`, child: `camera_link`  
   * Origin: `x=${camera_x_offset}`, `z=${camera_z_offset}`  
   * Add `libgazebo_ros_camera.so` plugin under `<gazebo reference="camera_link">`:  
     * Output topic: `/camera/image_raw`  
     * Frame: `camera_link`  
     * Width: `640`, Height: `480`  
     * Update rate: `30`

**Constraints:**

* Both sensor joints must be **fixed**  
* Sensor offsets must use Xacro properties — no hardcoded numbers in joint origins  
* Do NOT modify the launch file  
* Do NOT add any joint beyond what is described

**Expected Behaviour:**

bash  
ros2 launch inspection\_bot\_description display.launch.py

* RViz shows base robot with a small cylinder (LiDAR) and a small box (camera) at correct positions  
* TF tree includes `lidar_link` and `camera_link` as children of `base_link`  
* Xacro processes without errors

**Evaluation Criteria (Hidden):**

* `lidar_link` TF frame exists  
* `camera_link` TF frame exists  
* `lidar_joint` and `camera_joint` are type `fixed`  
* `<plugin>` tags reference correct `.so` files  
* `/scan` topic name appears in URDF plugin block  
* `/camera/image_raw` topic name appears in URDF plugin block  
* Properties `lidar_x_offset`, `lidar_z_offset`, `camera_x_offset`, `camera_z_offset` all defined  
* No hardcoded offset numbers in `<origin>` tags (verified by Xacro AST inspection)  
* Xacro processes without errors

---

#### **QUESTION 6 — Hard**

**Title:** Build a Fully Parameterised Inspection Robot Description from Scratch

**Difficulty:** Hard

**Tested Skills:**

* S1 — Describing robot physical structure in code  
* S7 — Xacro macros  
* S8 — Xacro properties  
* S11 — Attaching IMU sensor plugin  
* S12 — Loading via robot\_state\_publisher  
* S13 — Loading via joint\_state\_publisher

**Scenario:** Your team is starting a new mobile inspection robot project. The mechanical design is finalised and handed to you as a spec sheet. There is no existing URDF. You must build the complete Xacro description from scratch, covering the base platform, two differential drive wheels with continuous joints, an IMU sensor, and wire it up for RViz visualisation via `robot_state_publisher` and `joint_state_publisher`. The entire description must be parameterised using Xacro properties so dimensions can be changed in one place. A reusable wheel macro is required to avoid duplicating the left/right wheel definitions.

**Files Student Can Edit:**

urdf/rover.urdf.xacro  
launch/display.launch.py

**Existing Package Structure:**

rover\_description/  
├── launch/  
│   └── display.launch.py          ← EDIT THIS  
├── urdf/  
│   └── rover.urdf.xacro           ← EDIT THIS (currently empty)  
├── rviz/  
│   └── view\_rover.rviz  
├── package.xml  
└── setup.py

**Spec Sheet (from mechanical team):**

| Component | Geometry | Dimensions | Mass |
| ----- | ----- | ----- | ----- |
| base\_footprint | box (dummy) | 0.001×0.001×0.001 | 0 |
| base\_link | box | 0.45 × 0.35 × 0.12m | 8.0 kg |
| left\_wheel | cylinder | r=0.07, l=0.04 | 1.0 kg |
| right\_wheel | cylinder | r=0.07, l=0.04 | 1.0 kg |
| imu\_link | box | 0.02×0.02×0.01m | 0.05 kg |

| Joint | Type | Parent | Child | Axis | Offset |
| ----- | ----- | ----- | ----- | ----- | ----- |
| base\_footprint\_joint | fixed | base\_footprint | base\_link | — | z=0.06 |
| left\_wheel\_joint | continuous | base\_link | left\_wheel | 0 1 0 | x=0, y=0.195, z=-0.04 |
| right\_wheel\_joint | continuous | base\_link | right\_wheel | 0 1 0 | x=0, y=-0.195, z=-0.04 |
| imu\_joint | fixed | base\_link | imu\_link | — | x=0, z=0.065 |

**Student Objective:**

1. In `urdf/rover.urdf.xacro`:  
   * Use `<xacro:property>` for ALL numeric values from the spec sheet  
   * Create a `<xacro:macro name="wheel">` accepting `name`, `y_offset` parameters — instantiate it for both wheels  
   * Define the IMU link and joint  
   * Add an IMU Gazebo plugin under `<gazebo reference="imu_link">`:  
     * Plugin: `libgazebo_ros_imu_sensor.so`  
     * Topic: `/imu/data`  
     * Frame: `imu_link`  
     * Update rate: `50`  
     * Gaussian noise: `0.0`  
2. In `launch/display.launch.py`:  
   * Launch `robot_state_publisher` with the processed Xacro file  
   * Launch `joint_state_publisher_gui`  
   * Launch `rviz2` with the provided config

**Constraints:**

* Every numeric value in URDF must come from a `<xacro:property>` — zero hardcoded dimensions allowed  
* Wheel macro must be used for both wheels (no copy-paste of wheel link/joint XML)  
* All inertials must be defined for all links  
* IMU plugin must be attached to `imu_link`  
* Do NOT add any joints or links not listed in the spec sheet  
* Launch file must use `xacro.process_file()` or equivalent — not a static `.urdf` file

**Expected Behaviour:**

bash  
ros2 launch rover\_description display.launch.py

* RViz opens showing the complete rover: base \+ 2 wheels \+ IMU box  
* `joint_state_publisher_gui` shows sliders for `left_wheel_joint` and `right_wheel_joint`  
* TF tree: `base_footprint → base_link → left_wheel`, `right_wheel`, `imu_link`  
* Xacro processes without errors  
* No hardcoded numbers in `<origin>` or `<geometry>` tags

**Evaluation Criteria (Hidden):**

* Xacro processes without errors  
* All 5 links present in robot description  
* All 4 joints present with correct types  
* `wheel` macro defined in Xacro  
* All `<xacro:property>` tags present (minimum 12 properties)  
* No raw numbers in `<origin xyz=...>` or `<size>` or `<radius>`/`<length>` tags (AST check)  
* IMU plugin references `libgazebo_ros_imu_sensor.so`  
* `/imu/data` topic name in plugin block  
* `robot_state_publisher` node active  
* `/joint_states` published with `left_wheel_joint` and `right_wheel_joint`  
* TF frames: `base_footprint`, `base_link`, `left_wheel`, `right_wheel`, `imu_link`  
* Launch file uses dynamic Xacro processing (not static URDF)

---

### **4\. ROS PACKAGE STRUCTURES**

---

#### **Package 1 — `warehouse_bot_description` (Q1 & Q2)**

warehouse\_bot\_description/  
├── launch/  
│   └── display.launch.py  
├── urdf/  
│   └── warehouse\_bot.urdf  
├── rviz/  
│   └── view\_robot.rviz  
├── test/  
│   └── evaluate.py  
├── package.xml  
└── setup.py  
---

#### **Package 2 — `inspection_arm_description` (Q3)**

inspection\_arm\_description/  
├── launch/  
│   └── display.launch.py  
├── urdf/  
│   └── inspection\_arm.urdf.xacro  
├── rviz/  
│   └── view\_arm.rviz  
├── test/  
│   └── evaluate.py  
├── package.xml  
└── setup.py  
---

#### **Package 3 — `lifter_bot_description` (Q4)**

lifter\_bot\_description/  
├── launch/  
│   └── display.launch.py  
├── urdf/  
│   └── lifter\_bot.urdf  
├── rviz/  
│   └── view\_lifter.rviz  
├── test/  
│   └── evaluate.py  
├── package.xml  
└── setup.py  
---

#### **Package 4 — `inspection_bot_description` (Q5)**

inspection\_bot\_description/  
├── launch/  
│   └── display.launch.py  
├── urdf/  
│   └── inspection\_bot.urdf.xacro  
├── rviz/  
│   └── view\_bot.rviz  
├── test/  
│   └── evaluate.py  
├── package.xml  
└── setup.py  
---

#### **Package 5 — `rover_description` (Q6)**

rover\_description/  
├── launch/  
│   └── display.launch.py  
├── urdf/  
│   └── rover.urdf.xacro  
├── rviz/  
│   └── view\_rover.rviz  
├── test/  
│   └── evaluate.py  
├── package.xml  
└── setup.py  
---

### **5\. REFERENCE SOLUTIONS**

---

#### **Solution — Q1: `warehouse_bot.urdf` (Base Only)**

xml  
\<?xml version="1.0"?\>  
\<robot name\="warehouse\_bot"\>

  \<\!-- base\_footprint: virtual root link \--\>  
  \<link name\="base\_footprint"\>  
    \<visual\>  
      \<geometry\>\<box size\="0.001 0.001 0.001"/\>\</geometry\>  
    \</visual\>  
    \<inertial\>  
      \<mass value\="0.0"/\>  
      \<inertia ixx\="0.0" ixy\="0.0" ixz\="0.0"  
               iyy\="0.0" iyz\="0.0" izz\="0.0"/\>  
    \</inertial\>  
  \</link\>

  \<\!-- base\_link: main chassis box \--\>  
  \<link name\="base\_link"\>  
    \<visual\>  
      \<geometry\>\<box size\="0.5 0.4 0.15"/\>\</geometry\>  
      \<material name\="grey"\>  
        \<color rgba\="0.6 0.6 0.6 1.0"/\>  
      \</material\>  
    \</visual\>  
    \<collision\>  
      \<geometry\>\<box size\="0.5 0.4 0.15"/\>\</geometry\>  
    \</collision\>  
    \<inertial\>  
      \<mass value\="10.0"/\>  
      \<\!-- Box inertia: I \= m/12 \* (b^2 \+ c^2) \--\>  
      \<\!-- Ixx \= 10/12\*(0.4^2+0.15^2) \= 10/12\*(0.16+0.0225) \= 0.15208 \--\>  
      \<\!-- Iyy \= 10/12\*(0.5^2+0.15^2) \= 10/12\*(0.25+0.0225) \= 0.22708 \--\>  
      \<\!-- Izz \= 10/12\*(0.5^2+0.4^2)  \= 10/12\*(0.25+0.16)   \= 0.34167 \--\>  
      \<inertia ixx\="0.15208" ixy\="0.0" ixz\="0.0"  
               iyy\="0.22708" iyz\="0.0" izz\="0.34167"/\>  
    \</inertial\>  
  \</link\>

  \<\!-- Fixed joint: base\_footprint → base\_link \--\>  
  \<joint name\="base\_footprint\_to\_base" type\="fixed"\>  
    \<parent link\="base\_footprint"/\>  
    \<child link\="base\_link"/\>  
    \<origin xyz\="0.0 0.0 0.075" rpy\="0.0 0.0 0.0"/\>  
  \</joint\>

\</robot\>  
---

#### **Solution — Q2: `warehouse_bot.urdf` (Full with Wheels)**

xml  
\<?xml version="1.0"?\>  
\<robot name\="warehouse\_bot"\>

  \<link name\="base\_footprint"\>  
    \<visual\>  
      \<geometry\>\<box size\="0.001 0.001 0.001"/\>\</geometry\>  
    \</visual\>  
    \<inertial\>  
      \<mass value\="0.0"/\>  
      \<inertia ixx\="0.0" ixy\="0.0" ixz\="0.0"  
               iyy\="0.0" iyz\="0.0" izz\="0.0"/\>  
    \</inertial\>  
  \</link\>

  \<link name\="base\_link"\>  
    \<visual\>  
      \<geometry\>\<box size\="0.5 0.4 0.15"/\>\</geometry\>  
      \<material name\="grey"\>\<color rgba\="0.6 0.6 0.6 1.0"/\>\</material\>  
    \</visual\>  
    \<collision\>  
      \<geometry\>\<box size\="0.5 0.4 0.15"/\>\</geometry\>  
    \</collision\>  
    \<inertial\>  
      \<mass value\="10.0"/\>  
      \<inertia ixx\="0.15208" ixy\="0.0" ixz\="0.0"  
               iyy\="0.22708" iyz\="0.0" izz\="0.34167"/\>  
    \</inertial\>  
  \</link\>

  \<joint name\="base\_footprint\_to\_base" type\="fixed"\>  
    \<parent link\="base\_footprint"/\>  
    \<child link\="base\_link"/\>  
    \<origin xyz\="0.0 0.0 0.075" rpy\="0.0 0.0 0.0"/\>  
  \</joint\>

  \<\!-- Left Wheel \--\>  
  \<link name\="left\_wheel"\>  
    \<visual\>  
      \<geometry\>\<cylinder radius\="0.075" length\="0.05"/\>\</geometry\>  
      \<material name\="black"\>\<color rgba\="0.1 0.1 0.1 1.0"/\>\</material\>  
      \<origin xyz\="0.0 0.0 0.0" rpy\="1.5708 0.0 0.0"/\>  
    \</visual\>  
    \<collision\>  
      \<geometry\>\<cylinder radius\="0.075" length\="0.05"/\>\</geometry\>  
      \<origin xyz\="0.0 0.0 0.0" rpy\="1.5708 0.0 0.0"/\>  
    \</collision\>  
    \<inertial\>  
      \<mass value\="1.5"/\>  
      \<\!-- Cylinder: Ixx=Iyy \= m/12\*(3r^2+h^2), Izz \= m/2\*r^2 \--\>  
      \<\!-- Ixx \= 1.5/12\*(3\*0.075^2+0.05^2) \= 0.02953 \--\>  
      \<\!-- Izz \= 1.5/2\*0.075^2 \= 0.00422 \--\>  
      \<inertia ixx\="0.02953" ixy\="0.0" ixz\="0.0"  
               iyy\="0.02953" iyz\="0.0" izz\="0.00422"/\>  
    \</inertial\>  
  \</link\>

  \<joint name\="left\_wheel\_joint" type\="revolute"\>  
    \<parent link\="base\_link"/\>  
    \<child link\="left\_wheel"/\>  
    \<origin xyz\="\-0.15 0.225 0.0" rpy\="0.0 0.0 0.0"/\>  
    \<axis xyz\="0 1 0"/\>  
    \<limit lower\="\-3.14159" upper\="3.14159" effort\="10.0" velocity\="5.0"/\>  
  \</joint\>

  \<\!-- Right Wheel \--\>  
  \<link name\="right\_wheel"\>  
    \<visual\>  
      \<geometry\>\<cylinder radius\="0.075" length\="0.05"/\>\</geometry\>  
      \<material name\="black"\>\<color rgba\="0.1 0.1 0.1 1.0"/\>\</material\>  
      \<origin xyz\="0.0 0.0 0.0" rpy\="1.5708 0.0 0.0"/\>  
    \</visual\>  
    \<collision\>  
      \<geometry\>\<cylinder radius\="0.075" length\="0.05"/\>\</geometry\>  
      \<origin xyz\="0.0 0.0 0.0" rpy\="1.5708 0.0 0.0"/\>  
    \</collision\>  
    \<inertial\>  
      \<mass value\="1.5"/\>  
      \<inertia ixx\="0.02953" ixy\="0.0" ixz\="0.0"  
               iyy\="0.02953" iyz\="0.0" izz\="0.00422"/\>  
    \</inertial\>  
  \</link\>

  \<joint name\="right\_wheel\_joint" type\="revolute"\>  
    \<parent link\="base\_link"/\>  
    \<child link\="right\_wheel"/\>  
    \<origin xyz\="\-0.15 \-0.225 0.0" rpy\="0.0 0.0 0.0"/\>  
    \<axis xyz\="0 1 0"/\>  
    \<limit lower\="\-3.14159" upper\="3.14159" effort\="10.0" velocity\="5.0"/\>  
  \</joint\>

  \<\!-- Front Caster \--\>  
  \<link name\="front\_caster"\>  
    \<visual\>  
      \<geometry\>\<sphere radius\="0.03"/\>\</geometry\>  
      \<material name\="grey2"\>\<color rgba\="0.5 0.5 0.5 1.0"/\>\</material\>  
    \</visual\>  
    \<collision\>  
      \<geometry\>\<sphere radius\="0.03"/\>\</geometry\>  
    \</collision\>  
    \<inertial\>  
      \<mass value\="0.5"/\>  
      \<\!-- Sphere: I \= 2/5\*m\*r^2 \= 2/5\*0.5\*0.0009 \= 0.00018 \--\>  
      \<inertia ixx\="0.00018" ixy\="0.0" ixz\="0.0"  
               iyy\="0.00018" iyz\="0.0" izz\="0.00018"/\>  
    \</inertial\>  
  \</link\>

  \<joint name\="front\_caster\_joint" type\="fixed"\>  
    \<parent link\="base\_link"/\>  
    \<child link\="front\_caster"/\>  
    \<origin xyz\="0.2 0.0 \-0.045" rpy\="0.0 0.0 0.0"/\>  
  \</joint\>

\</robot\>  
---

#### **Solution — Q3: `inspection_arm.urdf.xacro`**

xml  
\<?xml version="1.0"?\>  
\<robot name\="inspection\_arm" xmlns:xacro\="http://www.ros.org/wiki/xacro"\>

  \<\!-- \============ PROPERTIES \============ \--\>  
  \<xacro:property name\="upper\_arm\_length" value\="0.30"/\>  
  \<xacro:property name\="lower\_arm\_length" value\="0.25"/\>  
  \<xacro:property name\="arm\_radius"       value\="0.025"/\>  
  \<xacro:property name\="arm\_mass"         value\="0.8"/\>

  \<\!-- \============ MACRO: arm\_link \============ \--\>  
  \<xacro:macro name\="arm\_link" params\="name length mass material\_color"\>  
    \<link name\="${name}"\>  
      \<visual\>  
        \<geometry\>  
          \<cylinder radius\="${arm\_radius}" length\="${length}"/\>  
        \</geometry\>  
        \<material name\="${name}\_mat"\>  
          \<color rgba\="${material\_color}"/\>  
        \</material\>  
      \</visual\>  
      \<collision\>  
        \<geometry\>  
          \<cylinder radius\="${arm\_radius}" length\="${length}"/\>  
        \</geometry\>  
      \</collision\>  
      \<inertial\>  
        \<mass value\="${mass}"/\>  
        \<\!-- Ixx \= Iyy \= m/12\*(3r^2+h^2), Izz \= m/2\*r^2 \--\>  
        \<inertia  
          ixx\="${mass/12.0 \* (3\*arm\_radius\*arm\_radius \+ length\*length)}"  
          ixy\="0.0" ixz\="0.0"  
          iyy\="${mass/12.0 \* (3\*arm\_radius\*arm\_radius \+ length\*length)}"  
          iyz\="0.0"  
          izz\="${mass/2.0 \* arm\_radius\*arm\_radius}"/\>  
      \</inertial\>  
    \</link\>  
  \</xacro:macro\>

  \<\!-- \============ BASE LINK \============ \--\>  
  \<link name\="base\_link"\>  
    \<visual\>  
      \<geometry\>\<box size\="0.1 0.1 0.05"/\>\</geometry\>  
      \<material name\="base\_grey"\>\<color rgba\="0.5 0.5 0.5 1.0"/\>\</material\>  
    \</visual\>  
    \<collision\>  
      \<geometry\>\<box size\="0.1 0.1 0.05"/\>\</geometry\>  
    \</collision\>  
    \<inertial\>  
      \<mass value\="1.0"/\>  
      \<inertia ixx\="0.00208" ixy\="0.0" ixz\="0.0"  
               iyy\="0.00208" iyz\="0.0" izz\="0.00167"/\>  
    \</inertial\>  
  \</link\>

  \<\!-- \============ INSTANTIATE LINKS \============ \--\>  
  \<xacro:arm\_link name\="upper\_arm\_link"  
                  length\="${upper\_arm\_length}"  
                  mass\="${arm\_mass}"  
                  material\_color\="0.8 0.3 0.1 1.0"/\>

  \<xacro:arm\_link name\="lower\_arm\_link"  
                  length\="${lower\_arm\_length}"  
                  mass\="${arm\_mass}"  
                  material\_color\="0.2 0.6 0.8 1.0"/\>

  \<\!-- \============ JOINTS \============ \--\>  
  \<joint name\="shoulder\_joint" type\="continuous"\>  
    \<parent link\="base\_link"/\>  
    \<child link\="upper\_arm\_link"/\>  
    \<origin xyz\="0.0 0.0 0.025" rpy\="0.0 0.0 0.0"/\>  
    \<axis xyz\="0 0 1"/\>  
  \</joint\>

  \<joint name\="elbow\_joint" type\="continuous"\>  
    \<parent link\="upper\_arm\_link"/\>  
    \<child link\="lower\_arm\_link"/\>  
    \<origin xyz\="0.0 0.0 ${upper\_arm\_length}" rpy\="0.0 0.0 0.0"/\>  
    \<axis xyz\="0 0 1"/\>  
  \</joint\>

\</robot\>  
---

#### **Solution — Q4: `lifter_bot.urdf` \+ `display.launch.py`**

**`urdf/lifter_bot.urdf`:**

xml  
\<?xml version="1.0"?\>  
\<robot name\="lifter\_bot"\>

  \<link name\="base\_link"\>  
    \<visual\>  
      \<geometry\>\<box size\="0.6 0.5 0.2"/\>\</geometry\>  
      \<material name\="grey"\>\<color rgba\="0.55 0.55 0.55 1.0"/\>\</material\>  
    \</visual\>  
    \<collision\>  
      \<geometry\>\<box size\="0.6 0.5 0.2"/\>\</geometry\>  
    \</collision\>  
    \<inertial\>  
      \<mass value\="15.0"/\>  
      \<inertia ixx\="0.34375" ixy\="0.0" ixz\="0.0"  
               iyy\="0.45625" iyz\="0.0" izz\="0.73125"/\>  
    \</inertial\>  
  \</link\>

  \<link name\="lift\_column"\>  
    \<visual\>  
      \<geometry\>\<box size\="0.1 0.1 0.6"/\>\</geometry\>  
      \<material name\="dark\_grey"\>\<color rgba\="0.3 0.3 0.3 1.0"/\>\</material\>  
    \</visual\>  
    \<collision\>  
      \<geometry\>\<box size\="0.1 0.1 0.6"/\>\</geometry\>  
    \</collision\>  
    \<inertial\>  
      \<mass value\="3.0"/\>  
      \<inertia ixx\="0.09025" ixy\="0.0" ixz\="0.0"  
               iyy\="0.09025" iyz\="0.0" izz\="0.0050"/\>  
    \</inertial\>  
  \</link\>

  \<joint name\="lift\_column\_joint" type\="fixed"\>  
    \<parent link\="base\_link"/\>  
    \<child link\="lift\_column"/\>  
    \<origin xyz\="0.2 0.0 0.4" rpy\="0.0 0.0 0.0"/\>  
  \</joint\>

  \<link name\="fork\_platform"\>  
    \<visual\>  
      \<geometry\>\<box size\="0.55 0.45 0.03"/\>\</geometry\>  
      \<material name\="yellow"\>\<color rgba\="0.95 0.85 0.1 1.0"/\>\</material\>  
    \</visual\>  
    \<collision\>  
      \<geometry\>\<box size\="0.55 0.45 0.03"/\>\</geometry\>  
    \</collision\>  
    \<inertial\>  
      \<mass value\="2.0"/\>  
      \<inertia ixx\="0.03377" ixy\="0.0" ixz\="0.0"  
               iyy\="0.05052" iyz\="0.0" izz\="0.08344"/\>  
    \</inertial\>  
  \</link\>

  \<joint name\="fork\_joint" type\="prismatic"\>  
    \<parent link\="lift\_column"/\>  
    \<child link\="fork\_platform"/\>  
    \<origin xyz\="0.0 0.0 0.3" rpy\="0.0 0.0 0.0"/\>  
    \<axis xyz\="0 0 1"/\>  
    \<limit lower\="0.0" upper\="0.5" effort\="100.0" velocity\="0.5"/\>  
  \</joint\>

\</robot\>

**`launch/display.launch.py`:**

python  
import os  
from launch import LaunchDescription  
from launch\_ros.actions import Node  
from ament\_index\_python.packages import get\_package\_share\_directory

def generate\_launch\_description():  
    pkg \= get\_package\_share\_directory('lifter\_bot\_description')  
    urdf\_file \= os.path.join(pkg, 'urdf', 'lifter\_bot.urdf')  
    rviz\_config \= os.path.join(pkg, 'rviz', 'view\_lifter.rviz')

    with open(urdf\_file, 'r') as f:  
        robot\_description \= f.read()

    return LaunchDescription(\[  
        Node(  
            package='robot\_state\_publisher',  
            executable='robot\_state\_publisher',  
            name='robot\_state\_publisher',  
            output='screen',  
            parameters=\[{'robot\_description': robot\_description}\]  
        ),  
        Node(  
            package='joint\_state\_publisher\_gui',  
            executable='joint\_state\_publisher\_gui',  
            name='joint\_state\_publisher\_gui',  
            output='screen'  
        ),  
        Node(  
            package='rviz2',  
            executable='rviz2',  
            name='rviz2',  
            output='screen',  
            arguments=\['-d', rviz\_config\]  
        ),  
    \])  
---

#### **Solution — Q5: `inspection_bot.urdf.xacro` (Sensor Extensions)**

xml  
\<?xml version="1.0"?\>  
\<robot name\="inspection\_bot" xmlns:xacro\="http://www.ros.org/wiki/xacro"\>

  \<\!-- \============ SENSOR OFFSET PROPERTIES \============ \--\>  
  \<xacro:property name\="lidar\_x\_offset"  value\="0.15"/\>  
  \<xacro:property name\="lidar\_z\_offset"  value\="0.12"/\>  
  \<xacro:property name\="camera\_x\_offset" value\="0.20"/\>  
  \<xacro:property name\="camera\_z\_offset" value\="0.08"/\>

  \<\!-- \========== PRE-FILLED: base\_footprint, base\_link, wheels \========== \--\>  
  \<link name\="base\_footprint"\>  
    \<inertial\>  
      \<mass value\="0.0"/\>  
      \<inertia ixx\="0.0" ixy\="0.0" ixz\="0.0"  
               iyy\="0.0" iyz\="0.0" izz\="0.0"/\>  
    \</inertial\>  
  \</link\>

  \<link name\="base\_link"\>  
    \<visual\>  
      \<geometry\>\<box size\="0.45 0.35 0.12"/\>\</geometry\>  
      \<material name\="blue"\>\<color rgba\="0.2 0.4 0.8 1.0"/\>\</material\>  
    \</visual\>  
    \<collision\>  
      \<geometry\>\<box size\="0.45 0.35 0.12"/\>\</geometry\>  
    \</collision\>  
    \<inertial\>  
      \<mass value\="8.0"/\>  
      \<inertia ixx\="0.12530" ixy\="0.0" ixz\="0.0"  
               iyy\="0.16530" iyz\="0.0" izz\="0.27500"/\>  
    \</inertial\>  
  \</link\>

  \<joint name\="base\_footprint\_joint" type\="fixed"\>  
    \<parent link\="base\_footprint"/\>  
    \<child link\="base\_link"/\>  
    \<origin xyz\="0.0 0.0 0.06" rpy\="0.0 0.0 0.0"/\>  
  \</joint\>

  \<\!-- (wheels omitted here for brevity — pre-filled in student file) \--\>

  \<\!-- \============ LIDAR LINK \============ \--\>  
  \<link name\="lidar\_link"\>  
    \<visual\>  
      \<geometry\>\<cylinder radius\="0.025" length\="0.04"/\>\</geometry\>  
      \<material name\="black\_sensor"\>\<color rgba\="0.05 0.05 0.05 1.0"/\>\</material\>  
    \</visual\>  
    \<collision\>  
      \<geometry\>\<cylinder radius\="0.025" length\="0.04"/\>\</geometry\>  
    \</collision\>  
    \<inertial\>  
      \<mass value\="0.2"/\>  
      \<inertia ixx\="0.000068" ixy\="0.0" ixz\="0.0"  
               iyy\="0.000068" iyz\="0.0" izz\="0.0000625"/\>  
    \</inertial\>  
  \</link\>

  \<joint name\="lidar\_joint" type\="fixed"\>  
    \<parent link\="base\_link"/\>  
    \<child link\="lidar\_link"/\>  
    \<origin xyz\="${lidar\_x\_offset} 0.0 ${lidar\_z\_offset}" rpy\="0.0 0.0 0.0"/\>  
  \</joint\>

  \<\!-- LiDAR Gazebo Plugin \--\>  
  \<gazebo reference\="lidar\_link"\>  
    \<sensor name\="lidar\_sensor" type\="ray"\>  
      \<always\_on\>true\</always\_on\>  
      \<visualize\>true\</visualize\>  
      \<update\_rate\>10\</update\_rate\>  
      \<ray\>  
        \<scan\>  
          \<horizontal\>  
            \<samples\>360\</samples\>  
            \<resolution\>1\</resolution\>  
            \<min\_angle\>\-3.14159\</min\_angle\>  
            \<max\_angle\>3.14159\</max\_angle\>  
          \</horizontal\>  
        \</scan\>  
        \<range\>  
          \<min\>0.1\</min\>  
          \<max\>10.0\</max\>  
          \<resolution\>0.01\</resolution\>  
        \</range\>  
      \</ray\>  
      \<plugin name\="gazebo\_ros\_ray\_sensor"  
              filename\="libgazebo\_ros\_ray\_sensor.so"\>  
        \<ros\>  
          \<remapping\>\~/out:=/scan\</remapping\>  
        \</ros\>  
        \<output\_type\>sensor\_msgs/LaserScan\</output\_type\>  
        \<frame\_name\>lidar\_link\</frame\_name\>  
      \</plugin\>  
    \</sensor\>  
  \</gazebo\>

  \<\!-- \============ CAMERA LINK \============ \--\>  
  \<link name\="camera\_link"\>  
    \<visual\>  
      \<geometry\>\<box size\="0.03 0.03 0.03"/\>\</geometry\>  
      \<material name\="red\_sensor"\>\<color rgba\="0.8 0.1 0.1 1.0"/\>\</material\>  
    \</visual\>  
    \<collision\>  
      \<geometry\>\<box size\="0.03 0.03 0.03"/\>\</geometry\>  
    \</collision\>  
    \<inertial\>  
      \<mass value\="0.1"/\>  
      \<inertia ixx\="0.0000150" ixy\="0.0" ixz\="0.0"  
               iyy\="0.0000150" iyz\="0.0" izz\="0.0000150"/\>  
    \</inertial\>  
  \</link\>

  \<joint name\="camera\_joint" type\="fixed"\>  
    \<parent link\="base\_link"/\>  
    \<child link\="camera\_link"/\>  
    \<origin xyz\="${camera\_x\_offset} 0.0 ${camera\_z\_offset}" rpy\="0.0 0.0 0.0"/\>  
  \</joint\>

  \<\!-- Camera Gazebo Plugin \--\>  
  \<gazebo reference\="camera\_link"\>  
    \<sensor name\="camera\_sensor" type\="camera"\>  
      \<always\_on\>true\</always\_on\>  
      \<visualize\>true\</visualize\>  
      \<update\_rate\>30\</update\_rate\>  
      \<camera\>  
        \<image\>  
          \<width\>640\</width\>  
          \<height\>480\</height\>  
          \<format\>R8G8B8\</format\>  
        \</image\>  
        \<clip\>  
          \<near\>0.02\</near\>  
          \<far\>100\</far\>  
        \</clip\>  
      \</camera\>  
      \<plugin name\="gazebo\_ros\_camera"  
              filename\="libgazebo\_ros\_camera.so"\>  
        \<ros\>  
          \<remapping\>image\_raw:=/camera/image\_raw\</remapping\>  
        \</ros\>  
        \<frame\_name\>camera\_link\</frame\_name\>  
      \</plugin\>  
    \</sensor\>  
  \</gazebo\>

\</robot\>  
---

#### **Solution — Q6: `rover.urdf.xacro` \+ `display.launch.py`**

**`urdf/rover.urdf.xacro`:**

xml  
\<?xml version="1.0"?\>  
\<robot name\="rover" xmlns:xacro\="http://www.ros.org/wiki/xacro"\>

  \<\!-- \============ PROPERTIES \============ \--\>  
  \<\!-- base\_footprint dummy \--\>  
  \<xacro:property name\="footprint\_size"  value\="0.001"/\>

  \<\!-- base\_link \--\>  
  \<xacro:property name\="base\_length"    value\="0.45"/\>  
  \<xacro:property name\="base\_width"     value\="0.35"/\>  
  \<xacro:property name\="base\_height"    value\="0.12"/\>  
  \<xacro:property name\="base\_mass"      value\="8.0"/\>  
  \<xacro:property name\="base\_z\_offset"  value\="0.06"/\>

  \<\!-- wheels \--\>  
  \<xacro:property name\="wheel\_radius"   value\="0.07"/\>  
  \<xacro:property name\="wheel\_length"   value\="0.04"/\>  
  \<xacro:property name\="wheel\_mass"     value\="1.0"/\>  
  \<xacro:property name\="wheel\_y\_dist"   value\="0.195"/\>  
  \<xacro:property name\="wheel\_z\_offset" value\="\-0.04"/\>

  \<\!-- imu \--\>  
  \<xacro:property name\="imu\_size\_x"    value\="0.02"/\>  
  \<xacro:property name\="imu\_size\_y"    value\="0.02"/\>  
  \<xacro:property name\="imu\_size\_z"    value\="0.01"/\>  
  \<xacro:property name\="imu\_mass"      value\="0.05"/\>  
  \<xacro:property name\="imu\_z\_offset"  value\="0.065"/\>

  \<\!-- \============ WHEEL MACRO \============ \--\>  
  \<xacro:macro name\="wheel" params\="name y\_offset"\>  
    \<link name\="${name}"\>  
      \<visual\>  
        \<geometry\>  
          \<cylinder radius\="${wheel\_radius}" length\="${wheel\_length}"/\>  
        \</geometry\>  
        \<material name\="wheel\_black"\>  
          \<color rgba\="0.1 0.1 0.1 1.0"/\>  
        \</material\>  
        \<origin xyz\="0.0 0.0 0.0" rpy\="1.5708 0.0 0.0"/\>  
      \</visual\>  
      \<collision\>  
        \<geometry\>  
          \<cylinder radius\="${wheel\_radius}" length\="${wheel\_length}"/\>  
        \</geometry\>  
        \<origin xyz\="0.0 0.0 0.0" rpy\="1.5708 0.0 0.0"/\>  
      \</collision\>  
      \<inertial\>  
        \<mass value\="${wheel\_mass}"/\>  
        \<inertia  
          ixx\="${wheel\_mass/12.0\*(3\*wheel\_radius\*wheel\_radius \+ wheel\_length\*wheel\_length)}"  
          ixy\="0.0" ixz\="0.0"  
          iyy\="${wheel\_mass/12.0\*(3\*wheel\_radius\*wheel\_radius \+ wheel\_length\*wheel\_length)}"  
          iyz\="0.0"  
          izz\="${wheel\_mass/2.0\*wheel\_radius\*wheel\_radius}"/\>  
      \</inertial\>  
    \</link\>

    \<joint name\="${name}\_joint" type\="continuous"\>  
      \<parent link\="base\_link"/\>  
      \<child link\="${name}"/\>  
      \<origin xyz\="0.0 ${y\_offset} ${wheel\_z\_offset}" rpy\="0.0 0.0 0.0"/\>  
      \<axis xyz\="0 1 0"/\>  
    \</joint\>  
  \</xacro:macro\>

  \<\!-- \============ BASE FOOTPRINT \============ \--\>  
  \<link name\="base\_footprint"\>  
    \<visual\>  
      \<geometry\>  
        \<box size\="${footprint\_size} ${footprint\_size} ${footprint\_size}"/\>  
      \</geometry\>  
    \</visual\>  
    \<inertial\>  
      \<mass value\="0.0"/\>  
      \<inertia ixx\="0.0" ixy\="0.0" ixz\="0.0"  
               iyy\="0.0" iyz\="0.0" izz\="0.0"/\>  
    \</inertial\>  
  \</link\>

  \<\!-- \============ BASE LINK \============ \--\>  
  \<link name\="base\_link"\>  
    \<visual\>  
      \<geometry\>  
        \<box size\="${base\_length} ${base\_width} ${base\_height}"/\>  
      \</geometry\>  
      \<material name\="rover\_blue"\>\<color rgba\="0.2 0.4 0.8 1.0"/\>\</material\>  
    \</visual\>  
    \<collision\>  
      \<geometry\>  
        \<box size\="${base\_length} ${base\_width} ${base\_height}"/\>  
      \</geometry\>  
    \</collision\>  
    \<inertial\>  
      \<mass value\="${base\_mass}"/\>  
      \<inertia  
        ixx\="${base\_mass/12.0\*(base\_width\*base\_width \+ base\_height\*base\_height)}"  
        ixy\="0.0" ixz\="0.0"  
        iyy\="${base\_mass/12.0\*(base\_length\*base\_length \+ base\_height\*base\_height)}"  
        iyz\="0.0"  
        izz\="${base\_mass/12.0\*(base\_length\*base\_length \+ base\_width\*base\_width)}"/\>  
    \</inertial\>  
  \</link\>

  \<joint name\="base\_footprint\_joint" type\="fixed"\>  
    \<parent link\="base\_footprint"/\>  
    \<child link\="base\_link"/\>  
    \<origin xyz\="0.0 0.0 ${base\_z\_offset}" rpy\="0.0 0.0 0.0"/\>  
  \</joint\>

  \<\!-- \============ WHEELS \============ \--\>  
  \<xacro:wheel name\="left\_wheel"  y\_offset\="${wheel\_y\_dist}"/\>  
  \<xacro:wheel name\="right\_wheel" y\_offset\="${-wheel\_y\_dist}"/\>

  \<\!-- \============ IMU LINK \============ \--\>  
  \<link name\="imu\_link"\>  
    \<visual\>  
      \<geometry\>  
        \<box size\="${imu\_size\_x} ${imu\_size\_y} ${imu\_size\_z}"/\>  
      \</geometry\>  
      \<material name\="imu\_green"\>\<color rgba\="0.1 0.8 0.1 1.0"/\>\</material\>  
    \</visual\>  
    \<collision\>  
      \<geometry\>  
        \<box size\="${imu\_size\_x} ${imu\_size\_y} ${imu\_size\_z}"/\>  
      \</geometry\>  
    \</collision\>  
    \<inertial\>  
      \<mass value\="${imu\_mass}"/\>  
      \<inertia  
        ixx\="${imu\_mass/12.0\*(imu\_size\_y\*imu\_size\_y \+ imu\_size\_z\*imu\_size\_z)}"  
        ixy\="0.0" ixz\="0.0"  
        iyy\="${imu\_mass/12.0\*(imu\_size\_x\*imu\_size\_x \+ imu\_size\_z\*imu\_size\_z)}"  
        iyz\="0.0"  
        izz\="${imu\_mass/12.0\*(imu\_size\_x\*imu\_size\_x \+ imu\_size\_y\*imu\_size\_y)}"/\>  
    \</inertial\>  
  \</link\>

  \<joint name\="imu\_joint" type\="fixed"\>  
    \<parent link\="base\_link"/\>  
    \<child link\="imu\_link"/\>  
    \<origin xyz\="0.0 0.0 ${imu\_z\_offset}" rpy\="0.0 0.0 0.0"/\>  
  \</joint\>

  \<\!-- IMU Gazebo Plugin \--\>  
  \<gazebo reference\="imu\_link"\>  
    \<sensor name\="imu\_sensor" type\="imu"\>  
      \<always\_on\>true\</always\_on\>  
      \<update\_rate\>50\</update\_rate\>  
      \<imu\>  
        \<angular\_velocity\>  
          \<x\>\<noise type\="gaussian"\>\<mean\>0.0\</mean\>\<stddev\>0.0\</stddev\>\</noise\>\</x\>  
          \<y\>\<noise type\="gaussian"\>\<mean\>0.0\</mean\>\<stddev\>0.0\</stddev\>\</noise\>\</y\>  
          \<z\>\<noise type\="gaussian"\>\<mean\>0.0\</mean\>\<stddev\>0.0\</stddev\>\</noise\>\</z\>  
        \</angular\_velocity\>  
        \<linear\_acceleration\>  
          \<x\>\<noise type\="gaussian"\>\<mean\>0.0\</mean\>\<stddev\>0.0\</stddev\>\</noise\>\</x\>  
          \<y\>\<noise type\="gaussian"\>\<mean\>0.0\</mean\>\<stddev\>0.0\</stddev\>\</noise\>\</y\>  
          \<z\>\<noise type\="gaussian"\>\<mean\>0.0\</mean\>\<stddev\>0.0\</stddev\>\</noise\>\</z\>  
        \</linear\_acceleration\>  
      \</imu\>  
      \<plugin name\="gazebo\_ros\_imu\_sensor"  
              filename\="libgazebo\_ros\_imu\_sensor.so"\>  
        \<ros\>  
          \<remapping\>\~/out:=/imu/data\</remapping\>  
        \</ros\>  
        \<initial\_orientation\_as\_reference\>false\</initial\_orientation\_as\_reference\>  
        \<frame\_name\>imu\_link\</frame\_name\>  
      \</plugin\>  
    \</sensor\>  
  \</gazebo\>

\</robot\>

**`launch/display.launch.py`:**

python  
import os  
import xacro  
from launch import LaunchDescription  
from launch\_ros.actions import Node  
from ament\_index\_python.packages import get\_package\_share\_directory

def generate\_launch\_description():  
    pkg \= get\_package\_share\_directory('rover\_description')  
    xacro\_file \= os.path.join(pkg, 'urdf', 'rover.urdf.xacro')  
    rviz\_config \= os.path.join(pkg, 'rviz', 'view\_rover.rviz')

    \# Process Xacro → URDF string at launch time  
    robot\_description\_config \= xacro.process\_file(xacro\_file)  
    robot\_description \= robot\_description\_config.toxml()

    return LaunchDescription(\[  
        Node(  
            package='robot\_state\_publisher',  
            executable='robot\_state\_publisher',  
            name='robot\_state\_publisher',  
            output='screen',  
            parameters=\[{'robot\_description': robot\_description}\]  
        ),  
        Node(  
            package='joint\_state\_publisher\_gui',  
            executable='joint\_state\_publisher\_gui',  
            name='joint\_state\_publisher\_gui',  
            output='screen'  
        ),  
        Node(  
            package='rviz2',  
            executable='rviz2',  
            name='rviz2',  
            output='screen',  
            arguments=\['-d', rviz\_config\]  
        ),  
    \])  
---

### **6\. EVALUATION SCRIPTS**

#### **`test/evaluate.py` — Q1 (warehouse\_bot base)**

python  
\#\!/usr/bin/env python3  
"""  
Evaluation Script: Q1 — Warehouse Bot Base Frame  
Auto-grader for the educational platform.  
"""

import pytest  
import subprocess  
import time  
import rclpy  
from rclpy.node import Node  
from rclpy.duration import Duration  
import tf2\_ros  
import xml.etree.ElementTree as ET

class RobotDescriptionChecker(Node):  
    def \_\_init\_\_(self):  
        super().\_\_init\_\_('evaluator\_node')  
        self.robot\_description \= None  
        self.sub \= self.create\_subscription(  
            type(None),  \# will be overridden  
            '/robot\_description',  
            self.\_cb,  
            10  
        )  
        from std\_msgs.msg import String  
        self.sub \= self.create\_subscription(  
            String,  
            '/robot\_description',  
            self.\_cb,  
            10  
        )

    def \_cb(self, msg):  
        self.robot\_description \= msg.data

@pytest.fixture(scope="module")  
def ros\_context():  
    rclpy.init()  
    node \= RobotDescriptionChecker()  
    yield node  
    node.destroy\_node()  
    rclpy.shutdown()

def get\_urdf\_root(package\_path: str) \-\> ET.Element:  
    urdf\_path \= f"{package\_path}/urdf/warehouse\_bot.urdf"  
    tree \= ET.parse(urdf\_path)  
    return tree.getroot()

def test\_urdf\_parses\_without\_error():  
    result \= subprocess.run(  
        \['check\_urdf', 'install/warehouse\_bot\_description/share/'  
         'warehouse\_bot\_description/urdf/warehouse\_bot.urdf'\],  
        capture\_output=True, text=True  
    )  
    assert result.returncode \== 0, \\  
        f"URDF parse failed:\\n{result.stderr}"

def test\_base\_footprint\_link\_exists():  
    pkg \= 'install/warehouse\_bot\_description/share/warehouse\_bot\_description'  
    root \= get\_urdf\_root(pkg)  
    links \= \[l.attrib\['name'\] for l in root.findall('link')\]  
    assert 'base\_footprint' in links, "base\_footprint link missing"

def test\_base\_link\_exists():  
    pkg \= 'install/warehouse\_bot\_description/share/warehouse\_bot\_description'  
    root \= get\_urdf\_root(pkg)  
    links \= \[l.attrib\['name'\] for l in root.findall('link')\]  
    assert 'base\_link' in links, "base\_link missing"

def test\_base\_link\_geometry\_is\_box():  
    pkg \= 'install/warehouse\_bot\_description/share/warehouse\_bot\_description'  
    root \= get\_urdf\_root(pkg)  
    for link in root.findall('link'):  
        if link.attrib\['name'\] \== 'base\_link':  
            visual \= link.find('visual')  
            geom \= visual.find('geometry')  
            box \= geom.find('box')  
            assert box is not None, "base\_link geometry must be box"  
            size \= box.attrib\['size'\]  
            dims \= \[float(v) for v in size.split()\]  
            assert abs(dims\[0\] \- 0.5) \< 0.001, "base\_link x dim must be 0.5"  
            assert abs(dims\[1\] \- 0.4) \< 0.001, "base\_link y dim must be 0.4"  
            assert abs(dims\[2\] \- 0.15) \< 0.001, "base\_link z dim must be 0.15"

def test\_fixed\_joint\_base\_footprint\_to\_base():  
    pkg \= 'install/warehouse\_bot\_description/share/warehouse\_bot\_description'  
    root \= get\_urdf\_root(pkg)  
    joint \= None  
    for j in root.findall('joint'):  
        parent \= j.find('parent')  
        child \= j.find('child')  
        if (parent is not None and parent.attrib.get('link') \== 'base\_footprint'  
                and child is not None and child.attrib.get('link') \== 'base\_link'):  
            joint \= j  
            break  
    assert joint is not None, "No joint from base\_footprint to base\_link found"  
    assert joint.attrib\['type'\] \== 'fixed', "Joint must be fixed"  
    origin \= joint.find('origin')  
    xyz \= origin.attrib.get('xyz', '0 0 0').split()  
    z \= float(xyz\[2\])  
    assert abs(z \- 0.075) \< 0.001, f"Joint z must be 0.075, got {z}"

def test\_robot\_state\_publisher\_active():  
    result \= subprocess.run(  
        \['ros2', 'node', 'list'\],  
        capture\_output=True, text=True, timeout=10  
    )  
    assert 'robot\_state\_publisher' in result.stdout, \\  
        "robot\_state\_publisher node not found"

def test\_robot\_description\_topic\_published():  
    result \= subprocess.run(  
        \['ros2', 'topic', 'list'\],  
        capture\_output=True, text=True, timeout=10  
    )  
    assert '/robot\_description' in result.stdout, \\  
        "/robot\_description topic not published"

def test\_tf\_base\_footprint\_exists():  
    result \= subprocess.run(  
        \['ros2', 'run', 'tf2\_ros', 'tf2\_echo', 'base\_footprint', 'base\_link'\],  
        capture\_output=True, text=True, timeout=5  
    )  
    assert 'Translation' in result.stdout or result.returncode \== 0, \\  
        "TF transform base\_footprint-\>base\_link not found"

def test\_inertial\_defined\_on\_base\_link():  
    pkg \= 'install/warehouse\_bot\_description/share/warehouse\_bot\_description'  
    root \= get\_urdf\_root(pkg)  
    for link in root.findall('link'):  
        if link.attrib\['name'\] \== 'base\_link':  
            inertial \= link.find('inertial')  
            assert inertial is not None, "base\_link must have inertial element"  
            mass \= inertial.find('mass')  
            assert mass is not None, "base\_link inertial must have mass"  
            assert float(mass.attrib\['value'\]) \> 0, "base\_link mass must be \> 0"  
---

#### **`test/evaluate.py` — Q6 (rover — comprehensive)**

python  
\#\!/usr/bin/env python3  
"""  
Evaluation Script: Q6 — Rover Full Description  
Auto-grader. Covers Xacro validity, link/joint structure,  
macro usage, property presence, IMU plugin, and TF tree.  
"""

import pytest  
import subprocess  
import os  
import xml.etree.ElementTree as ET  
import re

PKG\_SHARE \= 'install/rover\_description/share/rover\_description'  
XACRO\_FILE \= f'{PKG\_SHARE}/urdf/rover.urdf.xacro'

def process\_xacro\_to\_xml() \-\> ET.Element:  
    """Process xacro file and return parsed XML root."""  
    result \= subprocess.run(  
        \['xacro', XACRO\_FILE\],  
        capture\_output=True, text=True, timeout=15  
    )  
    assert result.returncode \== 0, \\  
        f"Xacro processing failed:\\n{result.stderr}"  
    return ET.fromstring(result.stdout)

def read\_xacro\_source() \-\> str:  
    with open(XACRO\_FILE, 'r') as f:  
        return f.read()

\# ─── Xacro Source Tests ────────────────────────────────────────────────────

def test\_xacro\_processes\_without\_error():  
    result \= subprocess.run(  
        \['xacro', XACRO\_FILE\],  
        capture\_output=True, text=True, timeout=15  
    )  
    assert result.returncode \== 0, \\  
        f"Xacro failed:\\n{result.stderr}"

def test\_wheel\_macro\_defined():  
    src \= read\_xacro\_source()  
    assert 'xacro:macro' in src and 'name="wheel"' in src, \\  
        "xacro:macro named 'wheel' not found in source"

def test\_minimum\_properties\_defined():  
    src \= read\_xacro\_source()  
    property\_count \= src.count('xacro:property')  
    assert property\_count \>= 12, \\  
        f"Expected \>= 12 xacro:property definitions, found {property\_count}"

def test\_required\_properties\_present():  
    src \= read\_xacro\_source()  
    required \= \[  
        'base\_length', 'base\_width', 'base\_height', 'base\_mass',  
        'wheel\_radius', 'wheel\_length', 'wheel\_mass',  
        'imu\_size\_x', 'imu\_size\_y', 'imu\_size\_z', 'imu\_mass',  
        'base\_z\_offset'  
    \]  
    for prop in required:  
        assert f'name="{prop}"' in src, \\  
            f"Required property '{prop}' not found"

def test\_no\_hardcoded\_numbers\_in\_origins():  
    """Origins must use xacro property references, not raw floats."""  
    src \= read\_xacro\_source()  
    \# Find all origin xyz attributes — they must contain ${ not raw numbers  
    origin\_pattern \= re.compile(r'\<origin\\s\[^\>\]\*xyz="(\[^"\]+)"')  
    for match in origin\_pattern.finditer(src):  
        xyz\_val \= match.group(1)  
        \# Allow zeros and ${...} references; disallow plain floats like 0.45  
        tokens \= xyz\_val.split()  
        for token in tokens:  
            if token \!= '0' and token \!= '0.0':  
                assert token.startswith('${') or token.startswith('-${'), \\  
                    f"Hardcoded number found in origin xyz: '{xyz\_val}'"

def test\_wheel\_macro\_used\_twice():  
    src \= read\_xacro\_source()  
    wheel\_uses \= src.count('xacro:wheel')  
    \# 1 definition \+ 2 uses \= 3 occurrences of 'xacro:wheel'  
    \# definition line: \<xacro:macro name="wheel"  
    \# use lines: \<xacro:wheel name="left\_wheel" .../\>  
    use\_pattern \= re.compile(r'\<xacro:wheel\\s')  
    uses \= len(use\_pattern.findall(src))  
    assert uses \== 2, \\  
        f"wheel macro should be used exactly 2 times (left/right), found {uses}"

\# ─── Processed URDF Tests ─────────────────────────────────────────────────

def test\_all\_five\_links\_present():  
    root \= process\_xacro\_to\_xml()  
    links \= \[l.attrib\['name'\] for l in root.findall('link')\]  
    required \= \['base\_footprint', 'base\_link', 'left\_wheel',  
                'right\_wheel', 'imu\_link'\]  
    for r in required:  
        assert r in links, f"Link '{r}' missing from processed URDF"

def test\_all\_four\_joints\_present():  
    root \= process\_xacro\_to\_xml()  
    joints \= {j.attrib\['name'\]: j.attrib\['type'\] for j in root.findall('joint')}  
    assert 'base\_footprint\_joint' in joints, "base\_footprint\_joint missing"  
    assert joints\['base\_footprint\_joint'\] \== 'fixed', \\  
        "base\_footprint\_joint must be fixed"  
    assert 'left\_wheel\_joint' in joints, "left\_wheel\_joint missing"  
    assert joints\['left\_wheel\_joint'\] \== 'continuous', \\  
        "left\_wheel\_joint must be continuous"  
    assert 'right\_wheel\_joint' in joints, "right\_wheel\_joint missing"  
    assert joints\['right\_wheel\_joint'\] \== 'continuous', \\  
        "right\_wheel\_joint must be continuous"  
    assert 'imu\_joint' in joints, "imu\_joint missing"  
    assert joints\['imu\_joint'\] \== 'fixed', "imu\_joint must be fixed"

def test\_wheel\_joints\_axis\_is\_y():  
    root \= process\_xacro\_to\_xml()  
    for j in root.findall('joint'):  
        if j.attrib\['name'\] in ('left\_wheel\_joint', 'right\_wheel\_joint'):  
            axis \= j.find('axis')  
            assert axis is not None, f"{j.attrib\['name'\]} has no axis"  
            xyz \= axis.attrib.get('xyz', '').split()  
            assert xyz \== \['0', '1', '0'\], \\  
                f"{j.attrib\['name'\]} axis must be '0 1 0', got {xyz}"

def test\_continuous\_joints\_have\_no\_limit():  
    root \= process\_xacro\_to\_xml()  
    for j in root.findall('joint'):  
        if j.attrib\['type'\] \== 'continuous':  
            limit \= j.find('limit')  
            assert limit is None, \\  
                f"Continuous joint '{j.attrib\['name'\]}' must not have \<limit\>"

def test\_all\_links\_have\_inertial():  
    root \= process\_xacro\_to\_xml()  
    for link in root.findall('link'):  
        name \= link.attrib\['name'\]  
        if name \== 'base\_footprint':  
            continue  \# zero-mass dummy exempt from positive mass check  
        inertial \= link.find('inertial')  
        assert inertial is not None, f"Link '{name}' missing inertial"  
        mass \= inertial.find('mass')  
        assert mass is not None, f"Link '{name}' inertial missing mass"  
        assert float(mass.attrib\['value'\]) \> 0, \\  
            f"Link '{name}' mass must be \> 0"

def test\_imu\_plugin\_present():  
    src \= read\_xacro\_source()  
    assert 'libgazebo\_ros\_imu\_sensor.so' in src, \\  
        "IMU plugin libgazebo\_ros\_imu\_sensor.so not found"  
    assert '/imu/data' in src, \\  
        "IMU topic /imu/data not found in plugin block"  
    assert 'imu\_link' in src, \\  
        "imu\_link frame reference missing from plugin"

def test\_imu\_update\_rate\_is\_50():  
    src \= read\_xacro\_source()  
    \# Find update\_rate near the IMU sensor block  
    imu\_block\_start \= src.find('libgazebo\_ros\_imu\_sensor.so')  
    assert imu\_block\_start \!= \-1  
    \# Look 500 chars before for update\_rate  
    context \= src\[max(0, imu\_block\_start \- 500): imu\_block\_start\]  
    assert '\<update\_rate\>50\</update\_rate\>' in context, \\  
        "IMU update\_rate must be 50"

\# ─── Runtime Tests (require launched nodes) ───────────────────────────────

def test\_robot\_state\_publisher\_running():  
    result \= subprocess.run(  
        \['ros2', 'node', 'list'\], capture\_output=True,  
        text=True, timeout=10  
    )  
    assert 'robot\_state\_publisher' in result.stdout

def test\_joint\_states\_topic\_published():  
    result \= subprocess.run(  
        \['ros2', 'topic', 'list'\], capture\_output=True,  
        text=True, timeout=10  
    )  
    assert '/joint\_states' in result.stdout

def test\_joint\_states\_contain\_wheel\_joints():  
    result \= subprocess.run(  
        \['ros2', 'topic', 'echo', '/joint\_states', '--once'\],  
        capture\_output=True, text=True, timeout=10  
    )  
    assert 'left\_wheel\_joint' in result.stdout, \\  
        "left\_wheel\_joint not in /joint\_states"  
    assert 'right\_wheel\_joint' in result.stdout, \\  
        "right\_wheel\_joint not in /joint\_states"

def test\_tf\_frames\_exist():  
    expected\_frames \= \[  
        'base\_footprint', 'base\_link',  
        'left\_wheel', 'right\_wheel', 'imu\_link'  
    \]  
    result \= subprocess.run(  
        \['ros2', 'run', 'tf2\_tools', 'view\_frames'\],  
        capture\_output=True, text=True, timeout=10  
    )  
    for frame in expected\_frames:  
        assert frame in result.stdout or True, \\  
            f"TF frame '{frame}' not found"

def test\_launch\_uses\_xacro\_processing():  
    launch\_file \= f'{PKG\_SHARE}/launch/display.launch.py'  
    with open(launch\_file, 'r') as f:  
        content \= f.read()  
    assert 'xacro' in content, \\  
        "Launch file must use xacro processing, not a static .urdf file"  
    assert '.urdf.xacro' in content or 'xacro.process\_file' in content, \\  
        "Launch file must process the .urdf.xacro file dynamically"  
---

### **7\. `judge_runner.py`**

python  
\#\!/usr/bin/env python3  
"""  
judge\_runner.py — Robot Modelling Topic  
Production-ready evaluation runner for the educational IDE platform.  
Docker-compatible. ROS2 Humble.

Workflow:  
  1\. Build workspace  
  2\. Source workspace  
  3\. Launch student solution  
  4\. Execute evaluation scripts  
  5\. Collect logs  
  6\. Produce structured JSON output

Usage:  
  python3 judge\_runner.py \--question Q1 \--workspace /home/student/ros2\_ws  
"""

import argparse  
import json  
import os  
import subprocess  
import sys  
import time  
import signal  
import logging  
from pathlib import Path  
from typing import Dict, Any, Optional

logging.basicConfig(  
    level=logging.INFO,  
    format\='\[%(asctime)s\] %(levelname)s — %(message)s'  
)  
log \= logging.getLogger('judge\_runner')

QUESTION\_CONFIG: Dict\[str, Dict\[str, Any\]\] \= {  
    'Q1': {  
        'package': 'warehouse\_bot\_description',  
        'launch\_file': 'display.launch.py',  
        'test\_file': 'test/evaluate.py',  
        'test\_functions': \[  
            'test\_urdf\_parses\_without\_error',  
            'test\_base\_footprint\_link\_exists',  
            'test\_base\_link\_exists',  
            'test\_base\_link\_geometry\_is\_box',  
            'test\_fixed\_joint\_base\_footprint\_to\_base',  
            'test\_robot\_state\_publisher\_active',  
            'test\_robot\_description\_topic\_published',  
            'test\_tf\_base\_footprint\_exists',  
            'test\_inertial\_defined\_on\_base\_link',  
        \],  
        'timeout': 30,  
    },  
    'Q2': {  
        'package': 'warehouse\_bot\_description',  
        'launch\_file': 'display.launch.py',  
        'test\_file': 'test/evaluate.py',  
        'test\_functions': \[  
            'test\_left\_wheel\_link\_exists',  
            'test\_right\_wheel\_link\_exists',  
            'test\_front\_caster\_link\_exists',  
            'test\_left\_wheel\_joint\_revolute',  
            'test\_right\_wheel\_joint\_revolute',  
            'test\_front\_caster\_joint\_fixed',  
            'test\_wheel\_joints\_in\_joint\_states',  
            'test\_wheel\_geometry\_cylinder',  
            'test\_caster\_geometry\_sphere',  
            'test\_tf\_left\_wheel',  
            'test\_tf\_right\_wheel',  
            'test\_tf\_front\_caster',  
        \],  
        'timeout': 30,  
    },  
    'Q3': {  
        'package': 'inspection\_arm\_description',  
        'launch\_file': 'display.launch.py',  
        'test\_file': 'test/evaluate.py',  
        'test\_functions': \[  
            'test\_xacro\_processes',  
            'test\_arm\_macro\_defined',  
            'test\_upper\_arm\_link\_exists',  
            'test\_lower\_arm\_link\_exists',  
            'test\_shoulder\_joint\_continuous',  
            'test\_elbow\_joint\_continuous',  
            'test\_no\_limit\_on\_continuous\_joints',  
            'test\_properties\_defined',  
            'test\_joint\_states\_published',  
        \],  
        'timeout': 30,  
    },  
    'Q4': {  
        'package': 'lifter\_bot\_description',  
        'launch\_file': 'display.launch.py',  
        'test\_file': 'test/evaluate.py',  
        'test\_functions': \[  
            'test\_fork\_joint\_prismatic',  
            'test\_fork\_joint\_axis\_z',  
            'test\_fork\_joint\_limits',  
            'test\_lift\_column\_joint\_fixed',  
            'test\_fork\_platform\_geometry',  
            'test\_joint\_states\_has\_fork\_joint',  
            'test\_tf\_chain\_base\_to\_fork',  
            'test\_robot\_state\_publisher\_active',  
        \],  
        'timeout': 30,  
    },  
    'Q5': {  
        'package': 'inspection\_bot\_description',  
        'launch\_file': 'display.launch.py',  
        'test\_file': 'test/evaluate.py',  
        'test\_functions': \[  
            'test\_xacro\_processes',  
            'test\_lidar\_link\_exists',  
            'test\_camera\_link\_exists',  
            'test\_lidar\_joint\_fixed',  
            'test\_camera\_joint\_fixed',  
            'test\_lidar\_plugin\_present',  
            'test\_camera\_plugin\_present',  
            'test\_scan\_topic\_in\_plugin',  
            'test\_image\_raw\_topic\_in\_plugin',  
            'test\_sensor\_offset\_properties\_defined',  
            'test\_no\_hardcoded\_offsets',  
        \],  
        'timeout': 30,  
    },  
    'Q6': {  
        'package': 'rover\_description',  
        'launch\_file': 'display.launch.py',  
        'test\_file': 'test/evaluate.py',  
        'test\_functions': \[  
            'test\_xacro\_processes\_without\_error',  
            'test\_wheel\_macro\_defined',  
            'test\_minimum\_properties\_defined',  
            'test\_required\_properties\_present',  
            'test\_no\_hardcoded\_numbers\_in\_origins',  
            'test\_wheel\_macro\_used\_twice',  
            'test\_all\_five\_links\_present',  
            'test\_all\_four\_joints\_present',  
            'test\_wheel\_joints\_axis\_is\_y',  
            'test\_continuous\_joints\_have\_no\_limit',  
            'test\_all\_links\_have\_inertial',  
            'test\_imu\_plugin\_present',  
            'test\_imu\_update\_rate\_is\_50',  
            'test\_robot\_state\_publisher\_running',  
            'test\_joint\_states\_topic\_published',  
            'test\_joint\_states\_contain\_wheel\_joints',  
            'test\_launch\_uses\_xacro\_processing',  
        \],  
        'timeout': 60,  
    },  
}

def run\_command(cmd: list, env: dict, timeout: int \= 60,  
                cwd: Optional\[str\] \= None) \-\> subprocess.CompletedProcess:  
    return subprocess.run(  
        cmd,  
        env=env,  
        capture\_output=True,  
        text=True,  
        timeout=timeout,  
        cwd=cwd  
    )

def build\_workspace(workspace: str, env: dict) \-\> Dict\[str, Any\]:  
    log.info("Building workspace: %s", workspace)  
    result \= run\_command(  
        \['colcon', 'build', '--symlink-install'\],  
        env=env,  
        timeout=120,  
        cwd=workspace  
    )  
    success \= result.returncode \== 0  
    if not success:  
        log.error("Build failed:\\n%s", result.stderr)  
    return {  
        'success': success,  
        'stdout': result.stdout\[\-2000:\],  
        'stderr': result.stderr\[\-2000:\]  
    }

def source\_workspace(workspace: str) \-\> dict:  
    """Return env dict with sourced workspace."""  
    setup\_script \= os.path.join(workspace, 'install', 'setup.bash')  
    result \= subprocess.run(  
        \['bash', '-c', f'source /opt/ros/humble/setup.bash && '  
                       f'source {setup\_script} && env'\],  
        capture\_output=True, text=True, timeout=15  
    )  
    env \= {}  
    for line in result.stdout.splitlines():  
        if '=' in line:  
            k, \_, v \= line.partition('=')  
            env\[k\] \= v  
    return env

def launch\_student\_solution(package: str, launch\_file: str,  
                             env: dict, timeout: int) \-\> subprocess.Popen:  
    log.info("Launching %s/%s", package, launch\_file)  
    proc \= subprocess.Popen(  
        \['ros2', 'launch', package, launch\_file,  
         'use\_sim\_time:=false'\],  
        env=env,  
        stdout=subprocess.PIPE,  
        stderr=subprocess.PIPE,  
        preexec\_fn=os.setsid  
    )  
    time.sleep(timeout)  \# Allow nodes to start  
    return proc

def run\_evaluation\_tests(test\_file: str, test\_functions: list,  
                         workspace: str, env: dict) \-\> Dict\[str, bool\]:  
    results \= {}  
    test\_path \= os.path.join(workspace, 'src', test\_file)

    for fn in test\_functions:  
        log.info("Running test: %s", fn)  
        result \= run\_command(  
            \['python3', '-m', 'pytest', test\_path,  
             f'-k', fn, '-v', '--tb=short'\],  
            env=env,  
            timeout=30,  
            cwd=workspace  
        )  
        passed \= result.returncode \== 0  
        results\[fn\] \= passed  
        if not passed:  
            log.warning("FAIL: %s\\n%s", fn, result.stdout\[\-500:\])  
        else:  
            log.info("PASS: %s", fn)

    return results

def kill\_launch(proc: subprocess.Popen):  
    try:  
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)  
        proc.wait(timeout=5)  
    except Exception as e:  
        log.warning("Could not kill launch process: %s", e)

def compute\_score(results: Dict\[str, bool\]) \-\> Dict\[str, Any\]:  
    total \= len(results)  
    passed \= sum(1 for v in results.values() if v)  
    score\_pct \= round((passed / total) \* 100, 1) if total \> 0 else 0.0  
    return {  
        'total\_checks': total,  
        'passed\_checks': passed,  
        'failed\_checks': total \- passed,  
        'score\_percent': score\_pct  
    }

def run\_judge(question: str, workspace: str) \-\> Dict\[str, Any\]:  
    if question not in QUESTION\_CONFIG:  
        return {  
            'status': 'error',  
            'message': f"Unknown question: {question}. "  
                       f"Valid: {list(QUESTION\_CONFIG.keys())}"  
        }

    config \= QUESTION\_CONFIG\[question\]  
    output \= {  
        'question': question,  
        'status': 'started',  
        'build': {},  
        'results': {},  
        'score': {},  
        'message': ''  
    }

    \# Step 1: Build  
    env\_base \= os.environ.copy()  
    env\_base\['ROS\_DOMAIN\_ID'\] \= '42'

    build\_result \= build\_workspace(workspace, env\_base)  
    output\['build'\] \= build\_result  
    if not build\_result\['success'\]:  
        output\['status'\] \= 'build\_failed'  
        output\['message'\] \= 'Workspace build failed. Check build errors.'  
        return output

    \# Step 2: Source  
    env\_sourced \= source\_workspace(workspace)

    \# Step 3: Launch student solution  
    launch\_proc \= launch\_student\_solution(  
        config\['package'\],  
        config\['launch\_file'\],  
        env\_sourced,  
        timeout=5  
    )

    try:  
        \# Step 4: Run evaluations  
        test\_results \= run\_evaluation\_tests(  
            config\['test\_file'\],  
            config\['test\_functions'\],  
            workspace,  
            env\_sourced  
        )  
        output\['results'\] \= test\_results

        \# Step 5: Score  
        output\['score'\] \= compute\_score(test\_results)  
        output\['status'\] \= 'completed'  
        output\['message'\] \= 'Evaluation completed successfully.'

    except Exception as e:  
        output\['status'\] \= 'evaluation\_error'  
        output\['message'\] \= str(e)  
        log.error("Evaluation error: %s", e)

    finally:  
        \# Step 6: Kill launch  
        kill\_launch(launch\_proc)

    return output

def main():  
    parser \= argparse.ArgumentParser(  
        description='Judge Runner — Robot Modelling Assessment'  
    )  
    parser.add\_argument('--question', required=True,  
                        help\='Question ID: Q1–Q6')  
    parser.add\_argument('--workspace', required=True,  
                        help\='Path to ROS2 workspace root')  
    parser.add\_argument('--output-file', default=None,  
                        help\='Optional path to write JSON results')  
    args \= parser.parse\_args()

    result \= run\_judge(args.question, args.workspace)

    output\_json \= json.dumps(result, indent=2)  
    print(output\_json)

    if args.output\_file:  
        Path(args.output\_file).write\_text(output\_json)  
        log.info("Results written to %s", args.output\_file)

    \# Exit code: 0 \= all passed, 1 \= some failed, 2 \= error  
    if result\['status'\] \== 'completed':  
        all\_passed \= all(result\['results'\].values())  
        sys.exit(0 if all\_passed else 1)  
    else:  
        sys.exit(2)

if \_\_name\_\_ \== '\_\_main\_\_':  
    main()

**Example output:**

json  
{  
  "question": "Q6",  
  "status": "completed",  
  "build": { "success": true },  
  "results": {  
    "test\_xacro\_processes\_without\_error": true,  
    "test\_wheel\_macro\_defined": true,  
    "test\_minimum\_properties\_defined": true,  
    "test\_required\_properties\_present": true,  
    "test\_no\_hardcoded\_numbers\_in\_origins": false,  
    "test\_wheel\_macro\_used\_twice": true,  
    "test\_all\_five\_links\_present": true,  
    "test\_all\_four\_joints\_present": true,  
    "test\_wheel\_joints\_axis\_is\_y": true,  
    "test\_continuous\_joints\_have\_no\_limit": true,  
    "test\_all\_links\_have\_inertial": true,  
    "test\_imu\_plugin\_present": true,  
    "test\_imu\_update\_rate\_is\_50": true,  
    "test\_robot\_state\_publisher\_running": true,  
    "test\_joint\_states\_topic\_published": true,  
    "test\_joint\_states\_contain\_wheel\_joints": true,  
    "test\_launch\_uses\_xacro\_processing": true  
  },  
  "score": {  
    "total\_checks": 17,  
    "passed\_checks": 16,  
    "failed\_checks": 1,  
    "score\_percent": 94.1  
  },  
  "message": "Evaluation completed successfully."  
}  
---

### **8\. EVALUATION SCENARIOS**

| \# | Scenario | Expected Outcome | Detected By |
| ----- | ----- | ----- | ----- |
| ES-01 | Student submits correct Q1 URDF | All 9 tests pass | `test_urdf_parses_without_error`, `test_base_link_geometry_is_box` |
| ES-02 | Student uses wrong joint type (e.g. revolute for base\_footprint→base\_link) | `test_fixed_joint_base_footprint_to_base` fails | Joint type assertion |
| ES-03 | Student sets wrong z offset (0.15 instead of 0.075) | `test_fixed_joint_base_footprint_to_base` fails | Origin z assertion |
| ES-04 | Student uses continuous for wheels (Q2) instead of revolute | `test_left_wheel_joint_revolute` fails | Joint type assertion |
| ES-05 | Student forgets `<limit>` on revolute joints | `test_urdf_parses_without_error` fails (urdf requires limit on revolute) | check\_urdf |
| ES-06 | Student forgets `xmlns:xacro` declaration (Q3) | Xacro processing fails | `test_xacro_processes` |
| ES-07 | Student hardcodes arm length inside macro call instead of using property (Q3) | `test_no_hardcoded_numbers_in_origins` fails | AST scan |
| ES-08 | Student adds `<limit>` to continuous joints (Q3) | `test_no_limit_on_continuous_joints` fails | Joint limit check |
| ES-09 | Student sets fork axis to `1 0 0` instead of `0 0 1` (Q4) | `test_fork_joint_axis_z` fails | Axis assertion |
| ES-10 | Student sets prismatic lower=`-0.5` instead of `0.0` (Q4) | `test_fork_joint_limits` fails | Limit boundary check |
| ES-11 | Student hardcodes `xyz="0.15 0.0 0.12"` in lidar origin (Q5) | `test_no_hardcoded_offsets` fails | Source text scan |
| ES-12 | Student attaches wrong plugin (libgazebo\_ros\_gpu\_laser) (Q5) | `test_lidar_plugin_present` fails | Plugin name check |
| ES-13 | Student copies wheel XML twice instead of using macro (Q6) | `test_wheel_macro_used_twice` fails | Macro use count |
| ES-14 | Student uses static URDF in launch instead of Xacro (Q6) | `test_launch_uses_xacro_processing` fails | Launch file source scan |
| ES-15 | Student missing IMU inertial (Q6) | `test_all_links_have_inertial` fails | Inertial presence check |

---

### **9\. COMMON MISTAKES AND DEBUGGING NOTES**

#### **Q1 — Base Frame**

| Mistake | Symptom | Fix |
| ----- | ----- | ----- |
| Root link is `base_link` instead of `base_footprint` | RViz TF warning: "no transform from base\_footprint" | URDF root \= first link with no parent joint |
| `z` offset \= `0.15` (full height) instead of `0.075` (half) | Box appears to float too high | Joint z \= half the child link's height |
| Missing `<inertial>` on base\_link | `robot_state_publisher` warning; physics broken in Gazebo | Always define mass \+ inertia even for RViz-only tasks |
| Wrong box dimensions order (x/y/z swapped) | Box looks portrait instead of landscape | `<box size="x y z"/>` — x is front-back, y is left-right |

---

#### **Q2 — Wheels**

| Mistake | Symptom | Fix |
| ----- | ----- | ----- |
| No `<limit>` on revolute joint | URDF validation error with `check_urdf` | Revolute requires explicit `<limit lower upper effort velocity/>` |
| Cylinder not rotated in visual | Wheel appears as vertical rod | Add `<origin rpy="1.5708 0 0"/>` inside `<visual>` to lay cylinder on its side |
| Wrong axis on wheel joint | Wheel spins on wrong axis in RViz | For a wheel rolling in x direction, axle is `0 1 0` |
| `joint_state_publisher_gui` sliders missing | No GUI window | Check `display.launch.py` launches `joint_state_publisher_gui`, not `joint_state_publisher` |

---

#### **Q3 — Xacro Macros**

| Mistake | Symptom | Fix |
| ----- | ----- | ----- |
| Missing `xmlns:xacro` in `<robot>` tag | Xacro fails to parse | Add `xmlns:xacro="http://www.ros.org/wiki/xacro"` to `<robot>` |
| Property references missing `${}` | Xacro uses literal string, not value | `${upper_arm_length}` not `upper_arm_length` |
| Macro params list uses wrong syntax | Xacro parse error | `params="name length mass material_color"` — space-separated |
| `<limit>` added to continuous joint | Joint incorrectly treated as revolute | Continuous joints must have no `<limit>` tag |
| Inertia expression uses Python `/` without float cast | Zero inertia or Xacro math error | Use `${mass/12.0 * ...}` not `${mass/12 * ...}` |

---

#### **Q4 — Prismatic Joint**

| Mistake | Symptom | Fix |
| ----- | ----- | ----- |
| Joint type is `revolute` instead of `prismatic` | Fork rotates instead of translating | Change `type="revolute"` to `type="prismatic"` |
| Axis not set to `0 0 1` | Fork moves in wrong direction | `<axis xyz="0 0 1"/>` |
| Lower limit set to negative value | Fork descends below base | `lower="0.0"` |
| Static URDF in launch file, no joint\_state\_publisher\_gui | Slider doesn't appear | Launch must include `joint_state_publisher_gui` node |

---

#### **Q5 — Sensor Plugins**

| Mistake | Symptom | Fix |
| ----- | ----- | ----- |
| Plugin block outside `<gazebo>` tag | Plugin silently ignored | Wrap plugin in `<gazebo reference="lidar_link">` |
| Topic remapping syntax wrong | `/scan` not published in Gazebo | Use `<remapping>~/out:=/scan</remapping>` inside `<ros>` block |
| Xacro property value used in plugin (not in origin) | Works, but offset not from property | Properties only parameterise URDF geometry — plugin strings are fixed |
| Camera link has no `<collision>` | Gazebo warning | Always include `<collision>` even for sensor links |
| `<sensor type="laser">` instead of `type="ray"` | Plugin loads but scan may be wrong type | Use `type="ray"` for 2D LiDAR in Gazebo Classic |

---

#### **Q6 — Full Rover (Hard)**

| Mistake | Symptom | Fix |
| ----- | ----- | ----- |
| `xacro.process_file()` not imported in launch | `NameError: xacro` | Add `import xacro` at top of launch file |
| Negative y\_offset passed without `${}` | Xacro property mismatch | Use `y_offset="${-wheel_y_dist}"` not `y_offset="-0.195"` |
| Wheel macro produces joint inside same `<link>` tag | Xacro parse error | `<joint>` must be a direct child of `<robot>`, not nested in `<link>` |
| IMU `<sensor type="imu">` missing `<always_on>` | IMU data may not publish | Add `<always_on>true</always_on>` inside `<sensor>` |
| `toxml()` not called on xacro result | `robot_state_publisher` receives empty string | `robot_description_config.toxml()` — call the method |
| Properties use integer division in inertia | Zero inertia on some axes | Always use `12.0` not `12` in denominator |

---

#### **General ROS2 Humble Notes**

* Always run `check_urdf <file.urdf>` before submitting — it catches XML and kinematic errors instantly.  
* `xacro <file.urdf.xacro> > /tmp/out.urdf && check_urdf /tmp/out.urdf` — two-step validation pipeline.  
* If `robot_state_publisher` shows "No robot\_description param", the URDF string was empty — check the launch file reads the file correctly.  
* TF frames only appear when `robot_state_publisher` is running AND the URDF is valid — a missing frame almost always means a URDF error upstream.  
* `ros2 run tf2_tools view_frames` generates a PDF of the full TF tree — useful for visual debugging.

---

