"""aiserver_pkg 启动文件。"""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument(
            'ws_host',
            default_value='0.0.0.0',
            description='WebSocket 监听地址',
        ),
        DeclareLaunchArgument(
            'ws_port',
            default_value='9090',
            description='WebSocket 监听端口',
        ),
        Node(
            package='aiserver_pkg',
            executable='aiserver_node',
            name='aiserver_node',
            output='screen',
            parameters=[{
                'ws_host': LaunchConfiguration('ws_host'),
                'ws_port': LaunchConfiguration('ws_port'),
            }],
        ),
    ])
