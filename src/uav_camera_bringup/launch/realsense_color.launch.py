from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def launch_setup(context, *args, **kwargs):
    image_width = int(LaunchConfiguration("image_width").perform(context))
    image_height = int(LaunchConfiguration("image_height").perform(context))

    return [
        Node(
            package="v4l2_camera",
            executable="v4l2_camera_node",
            namespace="/uav/camera/color",
            name="v4l2_camera",
            output="screen",
            parameters=[
                {
                    "video_device": LaunchConfiguration("video_device"),
                    "image_size": [image_width, image_height],
                    "pixel_format": "YUYV",
                    "output_encoding": "rgb8",
                    "camera_frame_id": LaunchConfiguration("camera_frame_id"),
                    "camera_info_url": LaunchConfiguration("camera_info_url"),
                    "power_line_frequency": 1,
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
            DeclareLaunchArgument("camera_frame_id", default_value="uav_realsense_color_optical_frame"),
            DeclareLaunchArgument("camera_info_url", default_value=""),
            OpaqueFunction(function=launch_setup),
        ]
    )
