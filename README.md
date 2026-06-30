# uav_ws

UAV Raspberry Pi camera streaming workspace for the Co-UV UAV-UGV disaster response project.

The first target is to publish RealSense color and depth images from the Raspberry Pi to the main PC over ROS 2 DDS.

## Initial Scope

- Publish RealSense color and depth images as ROS 2 `sensor_msgs/Image`
- Publish camera, network, system, and heartbeat status topics
- Keep Visual SLAM and ArUco detection on the main PC

## Packages

```text
src/
├── uav_camera_bringup/     # Launch/config files for USB and RGB-D camera startup
├── uav_camera_streamer/    # Camera stream health monitor
└── uav_camera_status/      # Heartbeat, network monitor, and system monitor nodes
```

## Main Topics

RealSense camera:

```text
/uav/camera/color/image_raw
/uav/camera/color/camera_info
/uav/camera/depth/image_rect_raw
/uav/camera/depth/camera_info
```

Status:

```text
/uav/heartbeat
/uav/camera/color/status
/uav/camera/depth/status
/uav/network/status
/uav/system/status
```

The default system launch uses V4L2 devices directly for stable Raspberry Pi bringup.
The `realsense2_camera` RGB-D launch is kept as an optional path for aligned depth and point cloud tests.

```text
/dev/video4  color, YUYV -> rgb8
/dev/video0  depth, Z16  -> 16UC1
/uav/camera/aligned_depth_to_color/image_raw
/uav/camera/depth/color/points
```

## Raspberry Pi Dependencies

Target OS:

```text
Ubuntu Server 22.04 LTS ARM64
ROS 2 Humble
```

Install the runtime dependencies on the Raspberry Pi:

```bash
sudo apt update
sudo apt install -y \
  ros-humble-ros-base \
  ros-humble-v4l2-camera \
  ros-humble-image-transport \
  ros-humble-compressed-image-transport \
  python3-colcon-common-extensions
```

For RealSense wrapper tests later:

```bash
sudo apt install -y ros-humble-realsense2-camera
```

## Build

```bash
cd ~/uav_ws
source /opt/ros/humble/setup.bash
colcon build --symlink-install
source install/setup.bash
```

## Run Color + Depth Streaming

```bash
ros2 launch uav_camera_bringup uav_camera_system.launch.py \
  network_interface:=wlan0
```

Override V4L2 devices if needed:

```bash
ros2 launch uav_camera_bringup uav_camera_system.launch.py \
  color_video_device:=/dev/video4 \
  depth_video_device:=/dev/video0 \
  image_width:=640 \
  image_height:=480 \
  fps:=30.0
```

## Main PC Checks

Use the same `ROS_DOMAIN_ID` on the Raspberry Pi and main PC.

```bash
ros2 topic list
ros2 topic hz /uav/camera/color/image_raw
ros2 topic bw /uav/camera/color/image_raw
ros2 topic hz /uav/camera/depth/image_rect_raw
ros2 topic bw /uav/camera/depth/image_rect_raw
ros2 topic echo /uav/heartbeat
ros2 topic echo /uav/camera/color/status
ros2 topic echo /uav/camera/depth/status
```

View the image:

```bash
rqt_image_view /uav/camera/color/image_raw
```

## RealSense D435if via V4L2

On this Raspberry Pi, the RealSense D435if V4L2 devices were identified as:

```text
/dev/video0  depth, Z16 16-bit depth
/dev/video2  infrared / greyscale
/dev/video4  RGB color, YUYV
```

For color-only V4L2 tests, use `/dev/video4`.
For depth-only V4L2 tests, use the custom `v4l2_depth_node` on `/dev/video0`.
For synchronized/aligned RGB-D, try the `realsense2_camera` based launch files after raw streams are stable.

Minimal color-only bringup:

```bash
ros2 launch uav_camera_bringup realsense_color.launch.py
```

Minimal depth-only bringup:

```bash
ros2 run uav_camera_streamer v4l2_depth_node --ros-args \
  -p video_device:=/dev/video0
```

Published image topics:

```text
/uav/camera/color/image_raw
/uav/camera/depth/image_rect_raw
```

Check the raw Image type:

```bash
ros2 topic info /uav/camera/color/image_raw
ros2 topic echo --once /uav/camera/color/image_raw/header
ros2 topic info /uav/camera/depth/image_rect_raw
ros2 topic echo --once /uav/camera/depth/image_rect_raw/header
```

Save one frame over SSH:

```bash
ros2 run uav_camera_streamer save_image_once --ros-args \
  -p image_topic:=/uav/camera/color/image_raw \
  -p output_path:=/tmp/uav_color_snapshot.jpg
```

Then inspect the file:

```bash
file /tmp/uav_color_snapshot.jpg
```

## Stage 2: Stream Stabilization

The second milestone is to make the stream repeatable before connecting Visual SLAM.

### Raspberry Pi Checks

Check that the camera is visible:

```bash
ls /dev/video*
v4l2-ctl --list-devices
v4l2-ctl --device=/dev/video0 --list-formats-ext
```

Install `v4l-utils` if `v4l2-ctl` is missing:

```bash
sudo apt install -y v4l-utils
```

### Resolution and FPS Test Matrix

Run one setting at a time and record FPS, bandwidth, delay feel, and frame drops.

```text
640x480  @ 15 fps
640x480  @ 30 fps
1280x720 @ 15 fps
1280x720 @ 30 fps
```

Example:

```bash
ros2 launch uav_camera_bringup uav_camera_system.launch.py \
  color_profile:=1280,720,30 \
  depth_profile:=640,480,30
```

On the main PC:

```bash
ros2 topic hz /uav/camera/color/image_raw
ros2 topic bw /uav/camera/color/image_raw
ros2 topic hz /uav/camera/depth/image_rect_raw
ros2 topic bw /uav/camera/depth/image_rect_raw
ros2 topic echo /uav/camera/color/status
ros2 topic echo /uav/camera/depth/status
ros2 topic echo /uav/network/status
ros2 topic echo /uav/system/status
```

The camera status message includes:

```text
ok
estimated_fps
last_frame_age_sec
last_frame_stamp_sec
camera_info_ok
camera_info_count
width / height / encoding
```

### CameraInfo

`realsense2_camera` publishes RealSense camera info automatically:

```text
/uav/camera/color/camera_info
/uav/camera/depth/camera_info
```

The checked-in file is only a placeholder:

```text
src/uav_camera_bringup/config/camera_info.yaml
```

Replace it with real calibration values before using ArUco pose estimation or Visual SLAM accuracy tests.

### DDS / Network Baseline

Use the same domain on every machine:

```bash
export ROS_DOMAIN_ID=23
```

If discovery is unstable across Wi-Fi, test both machines on the same AP first, then consider a Discovery Server.

### systemd Auto Start

A service template is included at:

```text
src/uav_camera_bringup/systemd/uav-camera.service
```

Install it on the Raspberry Pi after building:

```bash
sudo cp ~/uav_ws/src/uav_camera_bringup/systemd/uav-camera.service /etc/systemd/system/uav-camera.service
sudo systemctl daemon-reload
sudo systemctl enable uav-camera.service
sudo systemctl start uav-camera.service
```

Check logs:

```bash
systemctl status uav-camera.service
journalctl -u uav-camera.service -f
```

## Current Milestone

The first success criterion is:

```text
Raspberry Pi publishes:
  /uav/camera/color/image_raw
  /uav/camera/depth/image_rect_raw
  /uav/camera/color/camera_info
  /uav/camera/depth/camera_info
  /uav/heartbeat

Main PC receives:
  camera image with stable FPS
  heartbeat/status messages
  measurable topic bandwidth and latency
```
