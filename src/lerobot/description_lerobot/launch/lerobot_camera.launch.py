import os
from launch import LaunchDescription
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory

def generate_launch_description():
    # 获取包共享路径
    pkg_dir = get_package_share_directory('description_lerobot')
    urdf_path = os.path.join(pkg_dir, "urdf", "lerobot_camera.urdf")
    rviz_cfg_path = os.path.join(pkg_dir, "rviz", "lerobot_rviz.rviz")

    # 读取urdf文件完整文本
    with open(urdf_path, 'r', encoding='utf-8') as f:
        urdf_content = f.read()

    # 发布机器人模型状态
    robot_state_publisher = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        parameters=[{"robot_description": urdf_content}],
        output="screen"
    )

    # 关节状态发布器（滑块调节关节）
    joint_state_publisher = Node(
        package="joint_state_publisher",
        executable="joint_state_publisher",
        output="screen"
    )

    # 启动rviz加载配置
    rviz2 = Node(
        package="rviz2",
        executable="rviz2",
        arguments=["-d", rviz_cfg_path],
        output="screen"
    )

    return LaunchDescription([
        robot_state_publisher,
        joint_state_publisher,
        rviz2
    ])