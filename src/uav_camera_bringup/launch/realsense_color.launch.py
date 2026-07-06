from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def launch_setup(context, *args, **kwargs):
    image_width = int(LaunchConfiguration("image_width").perform(context))
    image_height = int(LaunchConfiguration("image_height").perform(context))

    return [
        Node(
            package="uav_camera_streamer",
            executable="v4l2_mjpeg_node",
            namespace="/uav/camera/color",
            name="v4l2_mjpeg_node",
            output="screen",
            parameters=[
                {
                    "video_device": LaunchConfiguration("video_device"),
                    "image_width": image_width,
                    "image_height": image_height,
                    "fps": LaunchConfiguration("fps"),
                    "frame_id": LaunchConfiguration("camera_frame_id"),
                    "image_topic": "image_raw/compressed",
                }
            ],
        )
    ]


def generate_launch_description():
    return LaunchDescription(
        [
            DeclareLaunchArgument("video_device", default_value="/dev/video4"),
            DeclareLaunchArgument("image_width", default_value="640"),
            DeclareLaunchArgument("image_height", default_value="480"),
            DeclareLaunchArgument("fps", default_value="15.0"),
            DeclareLaunchArgument("camera_frame_id", default_value="uav_realsense_color_optical_frame"),
            DeclareLaunchArgument("camera_info_url", default_value=""),
            OpaqueFunction(function=launch_setup),
        ]
    )
