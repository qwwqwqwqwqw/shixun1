"""aiserver_pkg 启动文件。"""
from launch import LaunchDescription  # pyright: ignore[reportMissingImports]
from launch.actions import DeclareLaunchArgument  # pyright: ignore[reportMissingImports]
from launch.substitutions import LaunchConfiguration  # pyright: ignore[reportMissingImports]
from launch_ros.actions import Node  # pyright: ignore[reportMissingImports]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument(
            'tcp_host',
            default_value='0.0.0.0',
            description='TCP Socket 监听地址',
        ),
        DeclareLaunchArgument(
            'tcp_port',
            default_value='9090',
            description='TCP Socket 监听端口',
        ),
        Node(
            package='aiserver_pkg',
            executable='aiserver_node',
            name='aiserver_node',
            output='screen',
            parameters=[{
                'tcp_host': LaunchConfiguration('tcp_host'),
                'tcp_port': LaunchConfiguration('tcp_port'),
            }],
        ),
    ])
