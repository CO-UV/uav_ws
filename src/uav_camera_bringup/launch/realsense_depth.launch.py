from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription(
        [
            DeclareLaunchArgument("camera_namespace", default_value="uav"),
            DeclareLaunchArgument("camera_name", default_value="camera"),
            DeclareLaunchArgument("serial_no", default_value=""),
            DeclareLaunchArgument("depth_profile", default_value="640,480,30"),
            Node(
                package="realsense2_camera",
                executable="realsense2_camera_node",
                namespace=LaunchConfiguration("camera_namespace"),
                name=LaunchConfiguration("camera_name"),
                output="screen",
                parameters=[
                    {
                        "serial_no": LaunchConfiguration("serial_no"),
                        "enable_color": False,
                        "enable_depth": True,
                        "enable_infra": False,
                        "enable_infra1": False,
                        "enable_infra2": False,
                        "enable_gyro": False,
                        "enable_accel": False,
                        "enable_motion": False,
                        "depth_module.depth_profile": LaunchConfiguration("depth_profile"),
                        "depth_module.depth_format": "Z16",
                    }
                ],
            ),
        ]
    )
