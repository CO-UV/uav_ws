from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    color_launch = PathJoinSubstitution(
        [FindPackageShare("uav_camera_bringup"), "launch", "realsense_color.launch.py"]
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument("color_video_device", default_value="/dev/video4"),
            DeclareLaunchArgument("depth_video_device", default_value="/dev/video0"),
            DeclareLaunchArgument("image_width", default_value="640"),
            DeclareLaunchArgument("image_height", default_value="480"),
            DeclareLaunchArgument("fps", default_value="30.0"),
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(color_launch),
                launch_arguments={
                    "video_device": LaunchConfiguration("color_video_device"),
                    "image_width": LaunchConfiguration("image_width"),
                    "image_height": LaunchConfiguration("image_height"),
                }.items(),
            ),
            Node(
                package="uav_camera_streamer",
                executable="v4l2_depth_node",
                name="v4l2_depth_node",
                output="screen",
                parameters=[
                    {
                        "video_device": LaunchConfiguration("depth_video_device"),
                        "image_width": LaunchConfiguration("image_width"),
                        "image_height": LaunchConfiguration("image_height"),
                        "fps": LaunchConfiguration("fps"),
                    }
                ],
            ),
        ]
    )
