import os
from launch import LaunchDescription
from launch.actions import ExecuteProcess, RegisterEventHandler, TimerAction
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from launch.event_handlers import OnProcessExit
from launch.substitutions import PathJoinSubstitution
import xacro
import re

def remove_comments(text):
    pattern = r'<!--(.*?)-->'
    return re.sub(pattern, '', text, flags=re.DOTALL)

def generate_launch_description():
    robot_name_in_model = 'lerobot'
    package_name = 'description_lerobot'
    urdf_name = "lerobot_camera.urdf"

    pkg_share = FindPackageShare(package=package_name).find(package_name) 
    urdf_model_path = os.path.join(pkg_share, f'urdf/{urdf_name}')

    # gazebo world 路径
    gazebo_world = os.path.join(pkg_share, 'gazebo_world', 'cabinet.world')

    # 控制器yaml路径 moveit_config/config/ros2_controllers.yaml
    controller_config_path = PathJoinSubstitution([
        FindPackageShare("moveit_config"),
        "config",
        "ros2_controllers.yaml"
    ])

    # 1. 启动Gazebo仿真环境
    start_gazebo_cmd = ExecuteProcess(
        cmd=['gazebo', '--verbose', gazebo_world, '-s', 'libgazebo_ros_init.so', '-s', 'libgazebo_ros_factory.so'],
        output='screen'
    )
    
    # 2. 独立controller_manager进程（解决找不到服务的核心）
    controller_manager_node = Node(
        package="controller_manager",
        executable="ros2_control_node",
        parameters=[controller_config_path],
        output="screen"
    )

    # 解析xacro/urdf，清除注释避免解析异常
    xacro_file = urdf_model_path
    doc = xacro.parse(open(xacro_file))
    xacro.process_doc(doc)
    params = {'robot_description': remove_comments(doc.toxml())}
    
    # 3. robot_state_publisher 发布机器人描述与tf
    node_robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        parameters=[{'use_sim_time': True}, params, {"publish_frequency": 15.0}],
        output='screen'
    )

    # 4. 在Gazebo中生成机械臂模型
    spawn_entity_cmd = Node(
        package='gazebo_ros', 
        executable='spawn_entity.py',
        arguments=['-entity', robot_name_in_model, '-topic', 'robot_description'],
        output='screen'
    )

    # ========== 自动加载控制器 ==========
    # 关节状态广播器
    load_joint_state_broadcaster = ExecuteProcess(
        cmd=['ros2', 'control', 'load_controller', '--set-state', 'active', 'joint_state_broadcaster'],
        output='screen',
    )
    # 手臂轨迹控制器
    load_group_controller = ExecuteProcess(
        cmd=['ros2', 'control', 'load_controller', '--set-state', 'active', 'lerobot_group_controller'],
        output='screen',
    )
    # 腕部+夹爪控制器
    load_gripper_controller = ExecuteProcess(
        cmd=['ros2', 'control', 'load_controller', '--set-state', 'active', 'lerobot_gripper_controller'],
        output='screen',
    )

    # 时序延时：模型生成完成后等待8秒再加载控制器
    delay_after_spawn = TimerAction(
        period=8.0,
        actions=[load_joint_state_broadcaster]
    )

    # 广播器启动2秒后，同时启动两组轨迹控制器
    delay_after_broadcaster = TimerAction(
        period=2.0,
        actions=[load_group_controller, load_gripper_controller]
    )

    # 事件绑定
    spawn_done_handler = RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=spawn_entity_cmd,
            on_exit=[delay_after_spawn],
        )
    )
    broadcaster_done_handler = RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=load_joint_state_broadcaster,
            on_exit=[delay_after_broadcaster],
        )
    )
    
    ld = LaunchDescription()
    ld.add_action(spawn_done_handler)
    ld.add_action(broadcaster_done_handler)

    # 固定启动顺序：Gazebo → controller_manager → robot_state_publisher → spawn模型
    ld.add_action(start_gazebo_cmd)
    ld.add_action(controller_manager_node)
    ld.add_action(node_robot_state_publisher)
    ld.add_action(spawn_entity_cmd)

    return ld