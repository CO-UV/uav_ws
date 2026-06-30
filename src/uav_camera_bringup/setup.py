from glob import glob
from setuptools import setup

package_name = "uav_camera_bringup"

setup(
    name=package_name,
    version="0.1.0",
    packages=[],
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{package_name}"]),
        (f"share/{package_name}", ["package.xml"]),
        (f"share/{package_name}/launch", glob("launch/*.launch.py")),
        (f"share/{package_name}/config", glob("config/*.yaml")),
        (f"share/{package_name}/systemd", glob("systemd/*.service")),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="Co-UV",
    maintainer_email="co-uv@example.com",
    description="Launch and configuration files for UAV camera streaming.",
    license="Apache-2.0",
)
