<!-- md_hash:346bbc12fa5bffbfb1b73d133081dfa8 -->
```markdown
## 1.  TOPIC ANALYSIS

SLAM Toolbox | ROS2 Humble | Ubuntu 22.04 | Python 3.10 | Gazebo Classic | RViz2

## 2.  SKILLS BEING TESTED

- S1: Running slam_toolbox to generate an occupancy grid map
- S2: Configuring slam_toolbox YAML parameters
- S3: Saving and serialising a completed map
- S4: Loading a saved map and launching AMCL-style localisation
- S5: Interpreting /map topic (OccupancyGrid)
- S6: Interpreting /scan topic (LaserScan)
- S7: Diagnosing mapping quality from /map and /scan topic data
- S8: Writing a ROS2 launch file that starts the full SLAM stack
- S9: Visualising SLAM output in RViz2
- S10: Using map_saver_cli to save .pgm and .yaml map files

## 3.  SIX CODING QUESTIONS

### QUESTION 1

- Skills: S1, S5, S6, S9
- Launch slam_toolbox node (async_slam_toolbox_node) with use_sim_time=true
- Launch rviz2 with slam_view.rviz
- Subscribe: /map (nav_msgs/OccupancyGrid)
- Compute: width, height, resolution, known_cells, free_cells, occupied_cells
- Publish /map_stats (std_msgs/String)

### QUESTION 2

- Skills: S1, S2, S8
- Write slam_toolbox parameter YAML matching site spec
- Launch full SLAM stack: gazebo_ros, robot_state_publisher, spawn_entity, async_slam_toolbox_node

### QUESTION 3

- Skills: S3, S10
- Implement MapSaverNode ROS2 node
- Subscribe: /save_map (std_msgs/String)
- Execute subprocess calls: map_saver_cli, /slam_toolbox/serialize_map
- Publish /save_map_status (std_msgs/String)

### QUESTION 4

- Skills: S4, S8, S9
- Write slam_toolbox parameter file for localisation mode
- Launch nodes: map_server, lifecycle_manager, robot_state_publisher, slam_toolbox, rviz2
- Configure rviz/localise_view.rviz

### QUESTION 5

- Skills: S5, S6, S7
- Implement MapDiagnostics ROS2 node
- Subscription A: /map (nav_msgs/OccupancyGrid)
- Subscription B: /scan (sensor_msgs/LaserScan)
- Timer at 0.5 Hz: compute and publish quality report
- Publish /map_quality_report (std_msgs/String)

### QUESTION 6

- Skills: S1/S2, S3/S10, S4, S5/S6/S7, S8/S9
- Write hospital_slam.yaml with 10 parameters
- Launch full mapping stack: robot_state_publisher, async_slam_toolbox_node, auto_map_saver, rviz2
- Implement AutoMapSaver ROS2 node
- Subscribe /map, /scan
- Timer at 1 Hz: check stability condition
- Publish /auto_save_status (std_msgs/String)
- Configure rviz/hospital_view.rviz

## 4.  ROS PACKAGE STRUCTURES

- slam_starter_pkg: start_slam.launch.py, slam_params.yaml, map_monitor.py, slam_view.rviz
- factory_slam_pkg: factory_slam.launch.py, factory_slam.yaml, factory_bot.urdf, factory_corridor.world
- map_save_pkg: save_map.launch.py, map_saver_node.py
- localisation_pkg: localise.launch.py, localise_params.yaml, warehouse_map files, localise_view.rviz, warehouse_bot.urdf
- map_diagnostics_pkg: diagnostics.launch.py, map_diagnostics.py
- hospital_slam_pkg: hospital_slam.launch.py, hospital_slam.yaml, auto_map_saver.py, hospital_view.rviz

## 5.  REFERENCE SOLUTIONS

### Solution — Q1: launch/start_slam.launch.py

- Node: slam_toolbox, rviz2

### Solution — Q1: scripts/map_monitor.py

- Subscribe: /map
- Publish: /map_stats

### Solution — Q2: config/factory_slam.yaml

- Parameters: mode, resolution, minimum_travel_distance, minimum_travel_heading, map_update_interval, max_laser_range, use_sim_time, scan_topic, odom_frame, base_frame, map_frame

### Solution — Q2: launch/factory_slam.launch.py

- IncludeLaunchDescription: gazebo
- Node: robot_state_publisher, spawn_entity, slam_toolbox

### Solution — Q3: scripts/map_saver_node.py

- Subscribe: /save_map
- Publish: /save_map_status
- Client: /slam_toolbox/serialize_map

### Solution — Q4: config/localise_params.yaml

- Parameters: mode, map_file_name, map_start_at_dock, use_sim_time, odom_frame, map_frame, base_frame, scan_topic, resolution

### Solution — Q4: launch/localise.launch.py

- LifecycleNode: map_server
- Node: lifecycle_manager, robot_state_publisher, slam_toolbox, rviz2

### Solution — Q5: scripts/map_diagnostics.py

- Subscribe: /map, /scan
- Publish: /map_quality_report

### Solution — Q6: scripts/auto_map_saver.py

- Subscribe: /map, /scan
- Publish: /auto_save_status
- Client: /slam_toolbox/serialize_map

### Solution — Q6: config/hospital_slam.yaml

- Parameters: mode, resolution, max_laser_range, minimum_travel_distance, minimum_travel_heading, map_update_interval, use_sim_time, scan_topic, odom_frame, base_frame, map_frame
```