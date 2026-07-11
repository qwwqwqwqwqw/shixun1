"""aiserver_pkg 启动文件。"""
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        Node(
            package='aiserver_pkg',
            executable='aiserver_node',
            name='aiserver_node',
            output='screen',
        ),
    ])
