from setuptools import find_packages, setup

package_name = "uav_camera_streamer"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{package_name}"]),
        (f"share/{package_name}", ["package.xml"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="Co-UV",
    maintainer_email="co-uv@example.com",
    description="Helper nodes for UAV camera stream health monitoring.",
    license="Apache-2.0",
    entry_points={
        "console_scripts": [
            "camera_health_node = uav_camera_streamer.camera_health_node:main",
            "save_image_once = uav_camera_streamer.save_image_once:main",
            "v4l2_depth_node = uav_camera_streamer.v4l2_depth_node:main",
            "v4l2_mjpeg_node = uav_camera_streamer.v4l2_mjpeg_node:main",
        ],
    },
)
