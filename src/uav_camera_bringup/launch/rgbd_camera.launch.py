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
            DeclareLaunchArgument("color_profile", default_value="640,480,30"),
            DeclareLaunchArgument("depth_profile", default_value="640,480,30"),
            DeclareLaunchArgument("enable_pointcloud", default_value="false"),
            DeclareLaunchArgument("align_depth", default_value="false"),
            DeclareLaunchArgument("enable_sync", default_value="false"),
            DeclareLaunchArgument("initial_reset", default_value="true"),
            Node(
                package="realsense2_camera",
                executable="realsense2_camera_node",
                namespace=LaunchConfiguration("camera_namespace"),
                name=LaunchConfiguration("camera_name"),
                output="screen",
                parameters=[
                    {
                        "serial_no": LaunchConfiguration("serial_no"),
                        "enable_color": True,
                        "enable_depth": True,
                        "enable_infra": False,
                        "enable_infra1": False,
                        "enable_infra2": False,
                        "enable_sync": LaunchConfiguration("enable_sync"),
                        "enable_gyro": False,
                        "enable_accel": False,
                        "enable_motion": False,
                        "initial_reset": LaunchConfiguration("initial_reset"),
                        "rgb_camera.color_profile": LaunchConfiguration("color_profile"),
                        "rgb_camera.color_format": "RGB8",
                        "rgb_camera.power_line_frequency": 1,
                        "depth_module.depth_profile": LaunchConfiguration("depth_profile"),
                        "depth_module.depth_format": "Z16",
                        "align_depth.enable": LaunchConfiguration("align_depth"),
                        "pointcloud.enable": LaunchConfiguration("enable_pointcloud"),
                    }
                ],
            ),
        ]
    )
