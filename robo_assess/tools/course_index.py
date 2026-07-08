"""
robo_assess.tools.course_index
==============================

Static index of robotics programming exercises curated from:
  - ETH Zurich "Programming for Robotics – ROS" (RSL)
  - Official ROS2 Tutorials (docs.ros.org/en/humble)
  - The Construct ROS2 Basics course
  - Open Robotics / ros2/examples GitHub
  - CMU 16-833 Robot Localization and Mapping
  - University of Michigan ROB 320

Used as a fallback when no web-search API key is configured.
score_exercise() ranks entries against a free-text query.
"""

from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# Exercise index
# ---------------------------------------------------------------------------

COURSE_EXERCISES: list[dict] = [
    # ── ETH RSL: Programming for Robotics ────────────────────────────────────
    # Lecture slides are publicly accessible as PDFs from the ETH CDN.
    # Exercise instructions live behind Moodle (login required).
    # Source for exercise descriptions: public slide PDFs at rsl.ethz.ch
    {
        "id": "eth_rsl_01",
        "source": "ETH RSL – Programming for Robotics",
        "title": "Create your first ROS2 node",
        "description": (
            "Write a minimal rclpy node that initialises, logs a greeting on startup, "
            "and spins until interrupted. The node must inherit from rclpy.node.Node "
            "and call rclpy.init() / rclpy.spin() / rclpy.shutdown() correctly."
        ),
        "difficulty": "easy",
        "skills": ["rclpy", "Node", "spin", "logging"],
        "ros_concepts": ["node lifecycle", "spin"],
        "url": "https://rsl.ethz.ch/education-students/lectures/ros.html",
    },
    {
        "id": "eth_rsl_02",
        "source": "ETH RSL – Programming for Robotics",
        "title": "Publish geometry_msgs/Twist to /cmd_vel",
        "description": (
            "Create a publisher node that publishes a geometry_msgs/Twist message to "
            "/cmd_vel at 10 Hz. Set linear.x to 0.5 m/s and angular.z to 0.2 rad/s. "
            "The timer callback must create and publish the message object every tick."
        ),
        "difficulty": "easy",
        "skills": ["publisher", "geometry_msgs", "Timer", "create_timer"],
        "ros_concepts": ["topics", "timer callbacks", "message types"],
        "url": "https://rsl.ethz.ch/education-students/lectures/ros.html",
    },
    {
        "id": "eth_rsl_03",
        "source": "ETH RSL – Programming for Robotics",
        "title": "Subscribe to /scan and compute average range",
        "description": (
            "Subscribe to /scan (sensor_msgs/LaserScan). In the callback, filter out "
            "inf/nan values from ranges[], compute the mean of valid readings, and log "
            "the result. Handle the empty-scan edge case."
        ),
        "difficulty": "easy",
        "skills": ["subscriber", "sensor_msgs", "LaserScan", "callback"],
        "ros_concepts": ["topics", "message callbacks", "data filtering"],
        "url": "https://rsl.ethz.ch/education-students/lectures/ros.html",
    },
    {
        "id": "eth_rsl_04",
        "source": "ETH RSL – Programming for Robotics",
        "title": "Declare and read a ROS2 parameter",
        "description": (
            "Write a node that declares a string parameter 'robot_name' with default "
            "'warehouse_bot' and an integer parameter 'max_speed_cm' with default 50. "
            "Read both on startup and log their values. Modify the node to accept the "
            "parameter values from the command line via ros2 run ... --ros-args -p."
        ),
        "difficulty": "easy",
        "skills": ["parameters", "declare_parameter", "get_parameter"],
        "ros_concepts": ["parameter server", "node parameters"],
        "url": "https://rsl.ethz.ch/education-students/lectures/ros.html",
    },
    {
        "id": "eth_rsl_05",
        "source": "ETH RSL – Programming for Robotics",
        "title": "Implement a service server and client",
        "description": (
            "Create a service server for std_srvs/srv/SetBool. When request.data is "
            "True, set an internal flag and return success=True, message='enabled'. "
            "When False, clear the flag. Create a separate client node that calls the "
            "service once on startup."
        ),
        "difficulty": "medium",
        "skills": ["service", "create_service", "SetBool", "client"],
        "ros_concepts": ["services", "request-response", "synchronous call"],
        "url": "https://rsl.ethz.ch/education-students/lectures/ros.html",
    },
    {
        "id": "eth_rsl_06",
        "source": "ETH RSL – Programming for Robotics",
        "title": "Broadcast and listen to a TF2 transform",
        "description": (
            "Part A: Write a TransformBroadcaster node that broadcasts a static "
            "transform from 'base_link' to 'sensor_frame' (translation: [0.1, 0, 0.5], "
            "no rotation) every 100 ms. "
            "Part B: Write a TransformListener node that looks up this transform and "
            "logs the translation vector."
        ),
        "difficulty": "medium",
        "skills": ["tf2_ros", "TransformBroadcaster", "TransformListener", "lookup_transform"],
        "ros_concepts": ["coordinate frames", "TF2 tree"],
        "url": "https://rsl.ethz.ch/education-students/lectures/ros.html",
    },
    {
        "id": "eth_rsl_07",
        "source": "ETH RSL – Programming for Robotics",
        "title": "Parse a URDF and read joint names",
        "description": (
            "Use the robot_description parameter (set by robot_state_publisher) to "
            "parse a URDF string with xml.etree.ElementTree. Extract all joint names "
            "with type != 'fixed' and publish them as a std_msgs/String on /joint_names."
        ),
        "difficulty": "medium",
        "skills": ["URDF", "robot_description", "xml", "robot_state_publisher"],
        "ros_concepts": ["robot description", "joint model"],
        "url": "https://rsl.ethz.ch/education-students/lectures/ros.html",
    },
    {
        "id": "eth_rsl_08",
        "source": "ETH RSL – Programming for Robotics",
        "title": "Create a launch file for two nodes",
        "description": (
            "Write a Python launch file that starts a talker node and a listener node "
            "from the same package. Pass a parameter 'queue_size' = 10 to the talker. "
            "Use Node() and DeclareLaunchArgument with LaunchConfiguration so the "
            "topic name can be overridden at the command line."
        ),
        "difficulty": "medium",
        "skills": ["launch", "Node", "LaunchConfiguration", "DeclareLaunchArgument"],
        "ros_concepts": ["launch system", "argument passing"],
        "url": "https://rsl.ethz.ch/education-students/lectures/ros.html",
    },

    # ── ROS2 Official Tutorials ───────────────────────────────────────────────
    {
        "id": "ros2_tut_01",
        "source": "ROS2 Official Tutorials (Humble)",
        "title": "Minimal publisher using rclpy",
        "description": (
            "Implement the canonical minimal publisher from the ROS2 docs: a node "
            "class with a timer that publishes String messages with an incrementing "
            "counter on /topic every 0.5 s. Package the node correctly in setup.py "
            "console_scripts."
        ),
        "difficulty": "easy",
        "skills": ["publisher", "std_msgs", "String", "create_timer"],
        "ros_concepts": ["topics", "publisher", "package structure"],
        "url": "https://docs.ros.org/en/humble/Tutorials/Beginner-Client-Libraries/Writing-A-Simple-Py-Publisher-And-Subscriber.html",
    },
    {
        "id": "ros2_tut_02",
        "source": "ROS2 Official Tutorials (Humble)",
        "title": "Minimal subscriber using rclpy",
        "description": (
            "Implement a subscriber node that listens on /topic (std_msgs/String) and "
            "logs each received message with its data field. The subscriber and "
            "publisher from the previous tutorial must communicate correctly."
        ),
        "difficulty": "easy",
        "skills": ["subscriber", "std_msgs", "callback", "create_subscription"],
        "ros_concepts": ["topics", "subscriber", "QoS"],
        "url": "https://docs.ros.org/en/humble/Tutorials/Beginner-Client-Libraries/Writing-A-Simple-Py-Publisher-And-Subscriber.html",
    },
    {
        "id": "ros2_tut_03",
        "source": "ROS2 Official Tutorials (Humble)",
        "title": "Simple service and client",
        "description": (
            "Implement a service node using example_interfaces/srv/AddTwoInts. The "
            "server receives a and b integers and responds with the sum. The client "
            "sends a single request on startup, waits for the response, and logs the "
            "result."
        ),
        "difficulty": "easy",
        "skills": ["service", "AddTwoInts", "create_service", "create_client", "call_async"],
        "ros_concepts": ["services", "synchronous RPC"],
        "url": "https://docs.ros.org/en/humble/Tutorials/Beginner-Client-Libraries/Writing-A-Simple-Py-Service-And-Client.html",
    },
    {
        "id": "ros2_tut_04",
        "source": "ROS2 Official Tutorials (Humble)",
        "title": "Using parameters in a Python node",
        "description": (
            "Create a node with a string parameter 'my_param' defaulting to 'world'. "
            "Add an on_set_parameters callback to validate that the value is never "
            "empty. Demonstrate parameter introspection with ros2 param list/get/set."
        ),
        "difficulty": "easy",
        "skills": ["parameters", "add_on_set_parameters_callback", "ParameterEventHandler"],
        "ros_concepts": ["dynamic parameters", "parameter validation"],
        "url": "https://docs.ros.org/en/humble/Tutorials/Beginner-Client-Libraries/Using-Parameters-In-A-Class-Python.html",
    },
    {
        "id": "ros2_tut_05",
        "source": "ROS2 Official Tutorials (Humble)",
        "title": "TF2 static broadcaster",
        "description": (
            "Write a node that uses StaticTransformBroadcaster to publish a fixed "
            "transform from 'world' to 'mystaticturtle' given x, y, z, roll, pitch, "
            "yaw command-line arguments. Verify with ros2 run tf2_ros tf2_echo."
        ),
        "difficulty": "easy",
        "skills": ["tf2_ros", "StaticTransformBroadcaster", "TransformStamped", "quaternion"],
        "ros_concepts": ["static transforms", "tf2"],
        "url": "https://docs.ros.org/en/humble/Tutorials/Intermediate/Tf2/Writing-A-Tf2-Static-Broadcaster-Py.html",
    },
    {
        "id": "ros2_tut_06",
        "source": "ROS2 Official Tutorials (Humble)",
        "title": "TF2 dynamic broadcaster (turtle follower)",
        "description": (
            "Create a TransformBroadcaster node that subscribes to /turtle1/pose "
            "(turtlesim/Pose) and continuously broadcasts the turtle's position as a "
            "TF2 frame named 'turtle1' relative to 'world'. Convert the 2D yaw to a "
            "quaternion using transforms3d or tf_transformations."
        ),
        "difficulty": "medium",
        "skills": ["tf2_ros", "TransformBroadcaster", "turtlesim", "quaternion_from_euler"],
        "ros_concepts": ["dynamic transforms", "pose to transform"],
        "url": "https://docs.ros.org/en/humble/Tutorials/Intermediate/Tf2/Writing-A-Tf2-Broadcaster-Py.html",
    },
    {
        "id": "ros2_tut_07",
        "source": "ROS2 Official Tutorials (Humble)",
        "title": "Custom message and service interface",
        "description": (
            "Define a custom message Sphere.msg (geometry_msgs/Point center, float64 "
            "radius) and a service ShapeDetection.srv (sensor_msgs/PointCloud2 cloud "
            "→ Sphere[] spheres). Build the interfaces package, then use the message "
            "in a publisher/subscriber pair."
        ),
        "difficulty": "medium",
        "skills": ["custom_msg", "custom_srv", "interface", "CMakeLists", "rosidl"],
        "ros_concepts": ["custom interfaces", "message generation"],
        "url": "https://docs.ros.org/en/humble/Tutorials/Beginner-Client-Libraries/Custom-ROS2-Interfaces.html",
    },
    {
        "id": "ros2_tut_08",
        "source": "ROS2 Official Tutorials (Humble)",
        "title": "Action server and client (Fibonacci)",
        "description": (
            "Implement an action server for action_tutorials_interfaces/action/Fibonacci. "
            "The server computes the Fibonacci sequence up to 'order', publishing "
            "partial_sequence as feedback on every step. The client sends a goal, "
            "handles feedback callbacks, and logs the final result."
        ),
        "difficulty": "hard",
        "skills": ["action", "ActionServer", "ActionClient", "feedback", "goal_handle"],
        "ros_concepts": ["actions", "long-running tasks", "feedback streaming"],
        "url": "https://docs.ros.org/en/humble/Tutorials/Intermediate/Writing-an-Action-Server-Client/Py.html",
    },

    # ── ros2/demos (Open Robotics GitHub — Apache 2.0) ────────────────────────
    {
        "id": "ros2_demo_01",
        "source": "ros2/demos (GitHub — Apache 2.0)",
        "title": "Move a robot in a square pattern",
        "description": (
            "Write a node that moves a differential-drive robot in a square: drive "
            "forward for 2 s at 0.2 m/s, rotate 90° at 0.5 rad/s, repeat four times. "
            "Use a state machine with create_timer and publish to /cmd_vel. Stop the "
            "robot (zero Twist) after completing one square."
        ),
        "difficulty": "medium",
        "skills": ["publisher", "geometry_msgs", "Twist", "Timer", "state machine"],
        "ros_concepts": ["open-loop control", "timed motion"],
        "url": "https://github.com/ros2/demos/tree/rolling/demo_nodes_py/demo_nodes_py/topics",
    },
    {
        "id": "ros2_demo_02",
        "source": "ros2/demos (GitHub — Apache 2.0)",
        "title": "Obstacle avoidance with LaserScan",
        "description": (
            "Subscribe to /scan (LaserScan). If any range in the front 30° arc (indices "
            "covering ±15° around 0°) is below 0.5 m, stop and rotate in place. "
            "Otherwise drive forward at 0.3 m/s. Publish commands to /cmd_vel. "
            "Handle inf values gracefully."
        ),
        "difficulty": "medium",
        "skills": ["subscriber", "LaserScan", "publisher", "geometry_msgs", "range filtering"],
        "ros_concepts": ["sensor-driven control", "reactive behaviour"],
        "url": "https://github.com/ros2/demos/tree/rolling/demo_nodes_py/demo_nodes_py/topics",
    },
    {
        "id": "ros2_demo_03",
        "source": "ros2/demos (GitHub — Apache 2.0)",
        "title": "Log odometry position to file",
        "description": (
            "Subscribe to /odom (nav_msgs/Odometry). Every 1 s, write the robot's "
            "x, y, yaw (extracted from quaternion) to a CSV file path given by a "
            "node parameter. Close the file cleanly on SIGINT via a destroy_node "
            "override."
        ),
        "difficulty": "easy",
        "skills": ["subscriber", "Odometry", "quaternion_to_euler", "file I/O", "parameters"],
        "ros_concepts": ["odometry", "lifecycle cleanup"],
        "url": "https://github.com/ros2/demos/tree/rolling/demo_nodes_py/demo_nodes_py",
    },
    {
        "id": "ros2_demo_04",
        "source": "ros2/demos (GitHub — Apache 2.0)",
        "title": "Camera image subscriber with pixel statistics",
        "description": (
            "Subscribe to /camera/image_raw (sensor_msgs/Image). Convert the raw "
            "bytes to a numpy array using the encoding field. Compute and publish the "
            "mean brightness (std_msgs/Float64) on /image/brightness. Support rgb8 "
            "and mono8 encodings."
        ),
        "difficulty": "medium",
        "skills": ["subscriber", "sensor_msgs/Image", "numpy", "encoding", "publisher"],
        "ros_concepts": ["image data", "numpy bridge"],
        "url": "https://github.com/ros2/demos/tree/rolling/image_tools/image_tools",
    },

    # ── ros2/examples (Open Robotics GitHub — Apache 2.0) ────────────────────
    {
        "id": "ros2_ex_01",
        "source": "ros2/examples (GitHub)",
        "title": "QoS-aware publisher and subscriber",
        "description": (
            "Create a publisher on /qos_chatter with BEST_EFFORT reliability and "
            "VOLATILE durability. Create a subscriber with matching QoS. Log a warning "
            "when messages are dropped. Demonstrate QoS incompatibility logging when "
            "connecting a RELIABLE subscriber."
        ),
        "difficulty": "medium",
        "skills": ["QoSProfile", "BEST_EFFORT", "VOLATILE", "publisher", "subscriber"],
        "ros_concepts": ["QoS policies", "reliability", "durability"],
        "url": "https://github.com/ros2/examples/tree/humble/rclpy/topics",
    },
    {
        "id": "ros2_ex_02",
        "source": "ros2/examples (GitHub)",
        "title": "MultiThreadedExecutor with reentrant callback group",
        "description": (
            "Create a node with two subscriptions that each do 200 ms of simulated "
            "processing. Use MultiThreadedExecutor and a ReentrantCallbackGroup so "
            "both callbacks run concurrently. Log thread IDs to verify parallelism."
        ),
        "difficulty": "hard",
        "skills": ["MultiThreadedExecutor", "ReentrantCallbackGroup", "threading", "executor"],
        "ros_concepts": ["executors", "callback groups", "concurrency"],
        "url": "https://github.com/ros2/examples/tree/humble/rclpy/executors",
    },
    {
        "id": "ros2_ex_03",
        "source": "ros2/examples (GitHub)",
        "title": "Composition: load a component node at runtime",
        "description": (
            "Write a component node (rclpy_components) that subscribes to /input "
            "(std_msgs/Int32) and republishes doubled values on /output. Register it "
            "as a composable node. Use ros2 component load to add it to a running "
            "component container without restarting."
        ),
        "difficulty": "hard",
        "skills": ["composition", "ComponentManager", "rclpy_components", "dynamic loading"],
        "ros_concepts": ["node composition", "component containers"],
        "url": "https://github.com/ros2/examples/tree/humble/rclpy/composition",
    },
    {
        "id": "ros2_ex_04",
        "source": "ros2/examples (GitHub)",
        "title": "Lifecycle node with managed transitions",
        "description": (
            "Implement a lifecycle node (LifecycleNode) with on_configure, on_activate, "
            "on_deactivate, and on_cleanup callbacks. on_configure creates a publisher; "
            "on_activate starts a 1 Hz timer; on_deactivate cancels the timer; "
            "on_cleanup destroys the publisher."
        ),
        "difficulty": "hard",
        "skills": ["LifecycleNode", "on_configure", "on_activate", "managed_node"],
        "ros_concepts": ["lifecycle", "state machine", "managed nodes"],
        "url": "https://github.com/ros2/examples/tree/humble/rclpy/lifecycle",
    },

    # ── Sensor processing ─────────────────────────────────────────────────────
    {
        "id": "sensor_01",
        "source": "Robotics Programming Exercises",
        "title": "IMU data subscriber with roll/pitch extraction",
        "description": (
            "Subscribe to /imu/data (sensor_msgs/Imu). Extract roll, pitch from the "
            "orientation quaternion using transforms3d.euler.quat2euler (or equivalent). "
            "Publish a custom TiltAngle.msg (float64 roll, float64 pitch) on /tilt. "
            "Log a warning when |pitch| > 15°."
        ),
        "difficulty": "medium",
        "skills": ["subscriber", "Imu", "quaternion_to_euler", "publisher", "custom_msg"],
        "ros_concepts": ["IMU", "quaternion math", "sensor fusion"],
        "url": "https://docs.ros.org/en/humble/",
    },
    {
        "id": "sensor_02",
        "source": "Robotics Programming Exercises",
        "title": "Battery state monitor with latched publisher",
        "description": (
            "Subscribe to /battery_state (sensor_msgs/BatteryState). When voltage "
            "drops below a parameter threshold (default 11.0 V), publish a "
            "diagnostic_msgs/DiagnosticStatus WARN on /diagnostics. Use TRANSIENT_LOCAL "
            "durability so late-joining subscribers get the last status."
        ),
        "difficulty": "medium",
        "skills": ["subscriber", "BatteryState", "DiagnosticStatus", "QoS", "TRANSIENT_LOCAL"],
        "ros_concepts": ["diagnostics", "latched topics", "QoS durability"],
        "url": "https://docs.ros.org/en/humble/",
    },
    {
        "id": "sensor_03",
        "source": "Robotics Programming Exercises",
        "title": "Joint state publisher for a 2-DOF arm",
        "description": (
            "Write a node that publishes sensor_msgs/JointState for joints ['shoulder', "
            "'elbow'] on /joint_states. Animate both joints: shoulder oscillates "
            "±45° at 0.5 Hz, elbow at 0.8 Hz. Include name, position, velocity, "
            "and effort arrays. Set the header stamp to now()."
        ),
        "difficulty": "easy",
        "skills": ["JointState", "publisher", "math.sin", "header", "stamp"],
        "ros_concepts": ["joint states", "robot visualisation"],
        "url": "https://docs.ros.org/en/humble/",
    },

    # ── Navigation / localization ──────────────────────────────────────────────
    {
        "id": "nav_01",
        "source": "Robotics Programming Exercises",
        "title": "Odometry accumulator from wheel encoders",
        "description": (
            "Subscribe to /wheel_ticks (std_msgs/Int32MultiArray, indices [left, right]). "
            "Accumulate distance using ticks_per_metre = 100. Compute x, y, theta via "
            "differential-drive kinematics (wheel_base = 0.3 m). Publish "
            "nav_msgs/Odometry on /odom_raw with a correct child_frame_id."
        ),
        "difficulty": "medium",
        "skills": ["subscriber", "Odometry", "kinematics", "publisher", "header"],
        "ros_concepts": ["dead reckoning", "differential drive"],
        "url": "https://docs.ros.org/en/humble/",
    },
    {
        "id": "nav_02",
        "source": "Robotics Programming Exercises",
        "title": "PoseStamped goal publisher for path planning",
        "description": (
            "Create a node that reads a YAML file (path given by parameter 'waypoints_file') "
            "containing a list of {x, y, yaw} waypoints. On a timer, publish the next "
            "waypoint as geometry_msgs/PoseStamped on /goal_pose, advancing through the "
            "list. Use yaw → quaternion conversion."
        ),
        "difficulty": "medium",
        "skills": ["PoseStamped", "yaml", "parameters", "publisher", "quaternion_from_euler"],
        "ros_concepts": ["goal pose", "waypoints", "path execution"],
        "url": "https://docs.ros.org/en/humble/",
    },

    # ── ROS2 bags ────────────────────────────────────────────────────────────
    {
        "id": "bag_01",
        "source": "ROS2 Official Tutorials (Humble)",
        "title": "Record and replay a topic with ros2 bag",
        "description": (
            "Write a launch file that starts a publisher on /chatter, records the bag "
            "for 5 s using ros2 bag record, then plays it back. Verify replay by "
            "subscribing and counting received messages in a pytest integration test."
        ),
        "difficulty": "medium",
        "skills": ["ros2bag", "launch", "record", "play", "integration testing"],
        "ros_concepts": ["data recording", "bag files", "replay"],
        "url": "https://docs.ros.org/en/humble/Tutorials/Beginner-CLI-Tools/Recording-And-Playing-Back-Data/Recording-And-Playing-Back-Data.html",
    },

    # ── Advanced patterns ────────────────────────────────────────────────────
    {
        "id": "adv_01",
        "source": "Robotics Programming Exercises",
        "title": "Synchronised subscriber with message_filters",
        "description": (
            "Use message_filters.ApproximateTimeSynchronizer to synchronise "
            "/camera/image_raw (sensor_msgs/Image) and /camera/camera_info "
            "(sensor_msgs/CameraInfo). In the callback, log the time delta between "
            "both message stamps. Set slop = 0.05 s, queue_size = 10."
        ),
        "difficulty": "hard",
        "skills": ["message_filters", "ApproximateTimeSynchronizer", "Image", "CameraInfo"],
        "ros_concepts": ["time synchronisation", "sensor fusion"],
        "url": "https://docs.ros.org/en/humble/",
    },
    {
        "id": "adv_02",
        "source": "Robotics Programming Exercises",
        "title": "Node with watchdog timer",
        "description": (
            "Create a node that subscribes to /heartbeat (std_msgs/Empty). If no "
            "message arrives within a parameter timeout (default 2.0 s), publish "
            "std_msgs/Bool False on /system/alive and log an ERROR. Reset the watchdog "
            "on each received heartbeat."
        ),
        "difficulty": "medium",
        "skills": ["subscriber", "publisher", "timer", "watchdog", "parameters"],
        "ros_concepts": ["watchdog pattern", "system health"],
        "url": "https://docs.ros.org/en/humble/",
    },
    {
        "id": "adv_03",
        "source": "Robotics Programming Exercises",
        "title": "Pluginlib-style strategy switcher via parameter",
        "description": (
            "Write a node with a 'control_mode' string parameter ('pid' or 'bang_bang'). "
            "Add an on_set_parameters callback that swaps between two internal controller "
            "objects at runtime without restarting. Publish /control_output (Float64) "
            "from the active controller every 50 ms."
        ),
        "difficulty": "hard",
        "skills": ["parameters", "on_set_parameters_callback", "strategy pattern", "publisher"],
        "ros_concepts": ["dynamic reconfiguration", "runtime strategy switching"],
        "url": "https://docs.ros.org/en/humble/",
    },
    {
        "id": "adv_04",
        "source": "ros2/demos (GitHub — Apache 2.0)",
        "title": "EKF-style covariance update via topics",
        "description": (
            "Subscribe to /odom (nav_msgs/Odometry, covariance from wheel odometry) "
            "and /imu/data (sensor_msgs/Imu). Implement a simple linear prediction step "
            "that blends the two covariance matrices using numpy. Publish the fused "
            "PoseWithCovarianceStamped on /pose_fused."
        ),
        "difficulty": "hard",
        "skills": ["Odometry", "Imu", "numpy", "covariance", "PoseWithCovarianceStamped"],
        "ros_concepts": ["sensor fusion", "covariance", "localisation"],
        "url": "https://github.com/ros2/demos/tree/rolling",
    },

    # ── henki-robotics/robotics_essentials_ros2 (Apache 2.0) ─────────────────
    {
        "id": "henki_01",
        "source": "henki-robotics/robotics_essentials_ros2 (GitHub — Apache 2.0)",
        "title": "Compute and publish robot odometry from wheel encoder ticks",
        "description": (
            "Subscribe to wheel encoder tick counts. Implement differential-drive "
            "forward kinematics to compute x, y, theta. Publish nav_msgs/Odometry "
            "on /odom with the correct header, child_frame_id, and covariance."
        ),
        "difficulty": "medium",
        "skills": ["Odometry", "kinematics", "subscriber", "publisher", "differential drive"],
        "ros_concepts": ["dead reckoning", "odometry"],
        "url": "https://github.com/henki-robotics/robotics_essentials_ros2/tree/main/4-robot_odometry",
    },
    {
        "id": "henki_02",
        "source": "henki-robotics/robotics_essentials_ros2 (GitHub — Apache 2.0)",
        "title": "Send a robot to a goal pose using a simple path planner",
        "description": (
            "Publish a goal as geometry_msgs/PoseStamped on /goal_pose. Subscribe to "
            "/odom to track current position. Compute heading error and drive toward "
            "the goal using a proportional controller on angular velocity. Stop when "
            "within a parameter tolerance."
        ),
        "difficulty": "medium",
        "skills": ["PoseStamped", "Odometry", "proportional controller", "publisher", "subscriber"],
        "ros_concepts": ["goal-directed navigation", "control loop"],
        "url": "https://github.com/henki-robotics/robotics_essentials_ros2/tree/main/5-path_planning",
    },
]


# ---------------------------------------------------------------------------
# Keyword scoring
# ---------------------------------------------------------------------------

def score_exercise(exercise: dict, query: str) -> float:
    """Return a relevance score [0, 1] for an exercise against a free-text query."""
    tokens = set(re.findall(r"[a-z0-9_]+", query.lower()))
    if not tokens:
        return 0.0

    searchable = " ".join([
        exercise.get("title", ""),
        exercise.get("description", ""),
        " ".join(exercise.get("skills", [])),
        " ".join(exercise.get("ros_concepts", [])),
    ]).lower()

    matches = sum(1 for t in tokens if t in searchable)
    return round(matches / len(tokens), 3)
