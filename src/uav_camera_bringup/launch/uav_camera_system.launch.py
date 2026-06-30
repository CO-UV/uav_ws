from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    camera_launch = PathJoinSubstitution(
        [FindPackageShare("uav_camera_bringup"), "launch", "v4l2_rgbd_camera.launch.py"]
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument("color_video_device", default_value="/dev/video4"),
            DeclareLaunchArgument("depth_video_device", default_value="/dev/video0"),
            DeclareLaunchArgument("image_width", default_value="640"),
            DeclareLaunchArgument("image_height", default_value="480"),
            DeclareLaunchArgument("fps", default_value="30.0"),
            DeclareLaunchArgument("network_interface", default_value="wlan0"),
            DeclareLaunchArgument("network_ping_host", default_value="8.8.8.8"),
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(camera_launch),
                launch_arguments={
                    "color_video_device": LaunchConfiguration("color_video_device"),
                    "depth_video_device": LaunchConfiguration("depth_video_device"),
                    "image_width": LaunchConfiguration("image_width"),
                    "image_height": LaunchConfiguration("image_height"),
                    "fps": LaunchConfiguration("fps"),
                }.items(),
            ),
            Node(
                package="uav_camera_streamer",
                executable="camera_health_node",
                name="color_camera_health_node",
                output="screen",
                parameters=[
                    {
                        "image_topic": "/uav/camera/color/image_raw",
                        "camera_info_topic": "/uav/camera/color/camera_info",
                        "status_topic": "/uav/camera/color/status",
                        "timeout_sec": 2.0,
                    }
                ],
            ),
            Node(
                package="uav_camera_streamer",
                executable="camera_health_node",
                name="depth_camera_health_node",
                output="screen",
                parameters=[
                    {
                        "image_topic": "/uav/camera/depth/image_rect_raw",
                        "camera_info_topic": "/uav/camera/depth/camera_info",
                        "status_topic": "/uav/camera/depth/status",
                        "timeout_sec": 2.0,
                    }
                ],
            ),
            Node(
                package="uav_camera_status",
                executable="heartbeat_node",
                name="heartbeat_node",
                output="screen",
            ),
            Node(
                package="uav_camera_status",
                executable="network_monitor_node",
                name="network_monitor_node",
                output="screen",
                parameters=[
                    {
                        "interface": LaunchConfiguration("network_interface"),
                        "ping_host": LaunchConfiguration("network_ping_host"),
                    }
                ],
            ),
            Node(
                package="uav_camera_status",
                executable="system_monitor_node",
                name="system_monitor_node",
                output="screen",
            ),
        ]
    )
