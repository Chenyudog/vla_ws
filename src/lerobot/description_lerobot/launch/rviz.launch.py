import launch
from launch_ros.actions import Node
import os
from launch import LaunchDescription
from launch.substitutions import Command
from ament_index_python.packages import get_package_share_directory
from launch_ros.parameter_descriptions import ParameterValue
def generate_launch_description():

    package_path=get_package_share_directory('description_lerobot')
    urdf_path=os.path.join(package_path, "urdf", "so_arm_100_5dof.urdf.xacro")
    rviz_config=os.path.join(package_path, "rviz", "lerobot_rviz.rviz")
    xacro_cmd= Command([
        "xacro ",
        urdf_path,
        " use_sim:=false"
    ])
    description_lerobot = ParameterValue(xacro_cmd, value_type=str)
    robot_state_publisher=Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        parameters=[{"robot_description":description_lerobot}],
        output="screen"
    )

    joint_state_publisher=Node(
        package="joint_state_publisher",
        executable="joint_state_publisher",
    )
    rviz2=Node(
        package="rviz2",
        executable="rviz2",
        arguments=["-d",rviz_config]
    )

    return LaunchDescription([
        robot_state_publisher,
        joint_state_publisher,
        rviz2
    ])
