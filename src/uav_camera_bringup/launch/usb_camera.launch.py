from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def launch_setup(context, *args, **kwargs):
    video_device = LaunchConfiguration("video_device")
    camera_frame_id = LaunchConfiguration("camera_frame_id")
    camera_info_url = LaunchConfiguration("camera_info_url")

    image_width = int(LaunchConfiguration("image_width").perform(context))
    image_height = int(LaunchConfiguration("image_height").perform(context))
    fps = int(LaunchConfiguration("fps").perform(context))

    return [
        Node(
            package="v4l2_camera",
            executable="v4l2_camera_node",
            namespace="/uav/camera/color",
            name="v4l2_camera",
            output="screen",
            parameters=[
                {
                    "video_device": video_device,
                    "image_size": [image_width, image_height],
                    "time_per_frame": [1, fps],
                    "camera_frame_id": camera_frame_id,
                    "camera_info_url": camera_info_url,
                }
            ],
        ),
        Node(
            package="image_transport",
            executable="republish",
            name="color_compressed_republisher",
            namespace="/uav/camera/color",
            output="screen",
            arguments=["raw", "compressed"],
            remappings=[
                ("in", "image_raw"),
                ("out", "image_raw"),
            ],
        ),
    ]


def generate_launch_description():
    return LaunchDescription(
        [
            DeclareLaunchArgument("video_device", default_value="/dev/video4"),
            DeclareLaunchArgument("image_width", default_value="640"),
            DeclareLaunchArgument("image_height", default_value="480"),
            DeclareLaunchArgument("fps", default_value="30"),
            DeclareLaunchArgument("camera_frame_id", default_value="uav_camera_color_optical_frame"),
            DeclareLaunchArgument("camera_info_url", default_value=""),
            OpaqueFunction(function=launch_setup),
        ]
    )
