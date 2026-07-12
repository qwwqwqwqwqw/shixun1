"""guide_pkg 一键启动文件 — 导航、到达融合和小程序手动控制。"""
from launch import LaunchDescription  # pyright: ignore[reportMissingImports]
from launch_ros.actions import Node  # pyright: ignore[reportMissingImports]


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
        Node(
            package='guide_pkg',
            executable='joystick_ctrl',
            name='joystick_ctrl',
            output='screen',
            parameters=[{'keyboard_control': False}],
        ),
    ])
