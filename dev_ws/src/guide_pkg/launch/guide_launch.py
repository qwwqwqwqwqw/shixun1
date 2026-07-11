"""guide_pkg 一键启动文件 — 同时启动 guide_node 和 arrival_fusion。"""
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        Node(
            package='guide_pkg',
            executable='guide_node',
            name='guide_node',
            output='screen',
        ),
        Node(
            package='guide_pkg',
            executable='arrival_fusion',
            name='arrival_fusion',
            output='screen',
        ),
    ])
