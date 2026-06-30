from setuptools import find_packages, setup

package_name = "uav_camera_status"

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
    description="Status, heartbeat, and system monitor nodes for the UAV Raspberry Pi.",
    license="Apache-2.0",
    entry_points={
        "console_scripts": [
            "heartbeat_node = uav_camera_status.heartbeat_node:main",
            "network_monitor_node = uav_camera_status.network_monitor_node:main",
            "system_monitor_node = uav_camera_status.system_monitor_node:main",
        ],
    },
)
