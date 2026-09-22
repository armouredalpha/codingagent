import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node
import xacro


def generate_launch_description():
    pkg = get_package_share_directory('robot_modeling')
    # BUG: wrong filename, should be burger_lidar.xacro
    xacro_file = os.path.join(pkg, 'urdf', 'burger.xacro')
    robot_description = xacro.process_file(xacro_file).toxml()

    rsp_node = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        parameters=[{'robot_description': robot_description}],
        output='screen',
    )

    return LaunchDescription([rsp_node])
