# uav_ws

Co-UV UAV-UGV 재난대응 프로젝트용 UAV 라즈베리파이 카메라 스트리밍 워크스페이스.

첫 번째 목표는 라즈베리파이에서 RealSense 컬러/뎁스 이미지를 ROS 2 DDS를 통해 메인 PC로 발행하는 것이다.

## 초기 범위

- RealSense 컬러/뎁스 이미지를 ROS 2 `sensor_msgs/Image`로 발행
- 카메라, 네트워크, 시스템, heartbeat 상태 토픽 발행
- Visual SLAM과 ArUco 인식은 메인 PC에 그대로 둠

## 패키지 구성

```text
src/
├── uav_camera_bringup/     # USB/RGB-D 카메라 기동용 launch/config 파일
├── uav_camera_streamer/    # 카메라 스트림 헬스 모니터
└── uav_camera_status/      # heartbeat, 네트워크 모니터, 시스템 모니터 노드
```

## 주요 토픽

RealSense 카메라 (기본 시스템 launch, 대역폭 절감을 위한 압축 전송):

```text
/uav/camera/color/image_raw/compressed   sensor_msgs/CompressedImage  (jpeg, ~15 fps)
/uav/camera/color/camera_info            sensor_msgs/CameraInfo
/uav/camera/depth/image_rect_raw/compressed  sensor_msgs/CompressedImage  (png, 요청 fps ~5)
/uav/camera/depth/camera_info            sensor_msgs/CameraInfo
```

상태:

```text
/uav/heartbeat
/uav/camera/color/status
/uav/camera/depth/status
/uav/network/status
/uav/system/status
```

기본 시스템 launch는 라즈베리파이에서 안정적으로 기동하기 위해 V4L2 디바이스를 직접 사용한다.
`realsense2_camera` RGB-D launch는 정렬된(depth-aligned) 뎁스와 포인트클라우드 테스트를 위한
선택적 경로로 남겨두었다 (이쪽은 여전히 비압축 `image_raw` / `image_rect_raw`를 발행한다).

```text
/dev/video4  color, YUYV (하드웨어에 MJPG 모드가 없음 — 아래처럼 JPEG는 소프트웨어로 인코딩)
/dev/video0  depth, Z16  -> 16UC1 (전송을 위해 PNG로 압축, 아래 참고)
/uav/camera/aligned_depth_to_color/image_raw
/uav/camera/depth/color/points
```

## 라즈베리파이 의존성

대상 OS:

```text
Ubuntu Server 22.04 LTS ARM64
ROS 2 Humble
```

라즈베리파이에 런타임 의존성 설치:

```bash
sudo apt update
sudo apt install -y \
  ros-humble-ros-base \
  ros-humble-v4l2-camera \
  ros-humble-image-transport \
  ros-humble-compressed-image-transport \
  python3-colcon-common-extensions
```

나중에 RealSense 래퍼 테스트용으로:

```bash
sudo apt install -y ros-humble-realsense2-camera
```

## 빌드

```bash
cd ~/uav_ws
source /opt/ros/humble/setup.bash
colcon build --symlink-install
source install/setup.bash
```

## 컬러 + 뎁스 스트리밍 실행

```bash
ros2 launch uav_camera_bringup uav_camera_system.launch.py \
  network_interface:=wlan0
```

필요하면 V4L2 디바이스 오버라이드:

```bash
ros2 launch uav_camera_bringup uav_camera_system.launch.py \
  color_video_device:=/dev/video4 \
  depth_video_device:=/dev/video0 \
  image_width:=640 \
  image_height:=480 \
  fps:=30.0
```

## 메인 PC 확인

라즈베리파이와 메인 PC에서 같은 `ROS_DOMAIN_ID`를 사용할 것.

```bash
ros2 topic list
ros2 topic hz /uav/camera/color/image_raw/compressed
ros2 topic bw /uav/camera/color/image_raw/compressed
ros2 topic hz /uav/camera/depth/image_rect_raw/compressed
ros2 topic bw /uav/camera/depth/image_rect_raw/compressed
ros2 topic echo /uav/heartbeat
ros2 topic echo /uav/camera/color/status
ros2 topic echo /uav/camera/depth/status
```

라즈베리파이가 실제로 발행 중인데도 `ros2 topic list`에 아무것도 안 뜨면, 대개
메인 PC의 `ros2 daemon`이 오래된 상태인 경우다 (데몬이 최초 실행될 때의
`ROS_DOMAIN_ID`/`ROS_DISCOVERY_SERVER`로 discovery 그래프를 캐시해두기 때문).
재시작하면 된다:

```bash
ros2 daemon stop
ros2 daemon start
```

이미지 확인 (rqt는 `sensor_msgs/CompressedImage`를 바로 디코드할 수 있다):

```bash
rqt_image_view /uav/camera/color/image_raw/compressed
```

## 메인 PC에서 각 토픽 수신하는 법

두 이미지 토픽 모두 raw `Image`가 아니라 `sensor_msgs/CompressedImage`다 —
OpenCV로 디코드하거나 (`format` 필드가 표준 `cv_bridge` 규약인
`"<encoding>; <codec> compressed"`를 따르므로) `image_transport`의 "compressed"
서브스크라이버로도 받을 수 있다.

**컬러** — `/uav/camera/color/image_raw/compressed`, `format: "bgr8; jpeg compressed"`:

```python
import cv2
import numpy as np

def on_color(msg):  # msg: sensor_msgs.msg.CompressedImage
    bgr = cv2.imdecode(np.frombuffer(msg.data, np.uint8), cv2.IMREAD_COLOR)
```

**뎁스** — `/uav/camera/depth/image_rect_raw/compressed`, `format: "16UC1; png compressed"`:

```python
def on_depth(msg):  # msg: sensor_msgs.msg.CompressedImage
    depth_mm = cv2.imdecode(np.frombuffer(msg.data, np.uint8), cv2.IMREAD_UNCHANGED)
    # depth_mm은 uint16 배열이며, 원본 16UC1 이미지와 동일한 밀리미터 단위다
```

**CameraInfo** — `/uav/camera/color/camera_info`, `/uav/camera/depth/camera_info`:
표준 `sensor_msgs/CameraInfo`이며, 대응하는 이미지와 함께 프레임마다 한 번씩 발행된다.
체크인된 `camera_info.yaml`은 아직 placeholder이니 아래 [CameraInfo](#camerainfo) 참고.

**상태 / heartbeat 토픽** — `std_msgs/String`에 JSON 페이로드가 담겨온다 (`json.loads(msg.data)`):

```text
/uav/camera/color/status, /uav/camera/depth/status
  {ok, image_topic, last_frame_age_sec, last_frame_stamp_sec, camera_info_ok,
   last_camera_info_age_sec, camera_info_count, frame_count, estimated_fps,
   width, height, encoding, camera_info_width, camera_info_height, camera_frame_id}

/uav/heartbeat
  {vehicle_id, hostname, sequence, stamp_unix_sec, uptime_sec, ok}

/uav/network/status
  {stamp_unix_sec, hostname, interface, ip_address, ping_host, ping_ok}

/uav/system/status
  {stamp_unix_sec, cpu_percent, load_average, memory, cpu_temperature_c}
```

카메라 상태 메시지의 `width`/`height`/`encoding`은 압축 토픽에서는 `null`이다
(측정할 raw 프레임이 없으므로) — 헬스체크에는 `estimated_fps`와 `ok`를 대신 사용할 것.

## RealSense D435if via V4L2

이 라즈베리파이에서 RealSense D435if의 V4L2 디바이스는 다음과 같이 확인되었다:

```text
/dev/video0  depth, Z16 16비트 뎁스
/dev/video2  적외선 / 그레이스케일
/dev/video4  RGB 컬러, YUYV
```

컬러 단독 V4L2 테스트는 `/dev/video4` 사용.
뎁스 단독 V4L2 테스트는 `/dev/video0`에서 커스텀 `v4l2_depth_node` 사용.
동기화된/정렬된 RGB-D는 raw 스트림이 안정된 뒤 `realsense2_camera` 기반 launch 파일로 시도.

컬러 단독 최소 기동:

```bash
ros2 launch uav_camera_bringup realsense_color.launch.py
```

뎁스 단독 최소 기동:

```bash
ros2 run uav_camera_streamer v4l2_depth_node --ros-args \
  -p video_device:=/dev/video0
```

발행되는 이미지 토픽:

```text
/uav/camera/color/image_raw
/uav/camera/depth/image_rect_raw
```

raw Image 타입 확인:

```bash
ros2 topic info /uav/camera/color/image_raw
ros2 topic echo --once /uav/camera/color/image_raw/header
ros2 topic info /uav/camera/depth/image_rect_raw
ros2 topic echo --once /uav/camera/depth/image_rect_raw/header
```

SSH로 프레임 한 장 저장:

```bash
ros2 run uav_camera_streamer save_image_once --ros-args \
  -p image_topic:=/uav/camera/color/image_raw \
  -p output_path:=/tmp/uav_color_snapshot.jpg
```

저장된 파일 확인:

```bash
file /tmp/uav_color_snapshot.jpg
```

## Stage 2: 스트림 안정화

두 번째 마일스톤은 Visual SLAM 연결 전에 스트림을 반복 가능하게 만드는 것이다.

### 라즈베리파이 확인

카메라가 인식되는지 확인:

```bash
ls /dev/video*
v4l2-ctl --list-devices
v4l2-ctl --device=/dev/video0 --list-formats-ext
```

`v4l2-ctl`이 없으면 `v4l-utils` 설치:

```bash
sudo apt install -y v4l-utils
```

### 해상도 / FPS 테스트 매트릭스

한 번에 하나씩 설정해서 FPS, 대역폭, 체감 지연, 프레임 드랍을 기록할 것.

```text
640x480  @ 15 fps
640x480  @ 30 fps
1280x720 @ 15 fps
1280x720 @ 30 fps
```

예시:

```bash
ros2 launch uav_camera_bringup uav_camera_system.launch.py \
  color_profile:=1280,720,30 \
  depth_profile:=640,480,30
```

메인 PC에서:

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

카메라 상태 메시지에는 다음이 포함된다:

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

`realsense2_camera`는 RealSense 카메라 정보를 자동으로 발행한다:

```text
/uav/camera/color/camera_info
/uav/camera/depth/camera_info
```

체크인된 파일은 아직 placeholder일 뿐이다:

```text
src/uav_camera_bringup/config/camera_info.yaml
```

ArUco 포즈 추정이나 Visual SLAM 정확도 테스트 전에 실제 캘리브레이션 값으로 교체할 것.

### DDS / 네트워크 기본 설정

모든 머신에서 동일한 도메인 사용:

```bash
export ROS_DOMAIN_ID=23
```

Wi-Fi 환경에서 discovery가 불안정하면 먼저 두 머신을 같은 AP에 붙여서 테스트하고,
그래도 안 되면 Discovery Server를 고려할 것.

### systemd 자동 시작

서비스 템플릿이 다음 경로에 포함되어 있다:

```text
src/uav_camera_bringup/systemd/uav-camera.service
```

빌드 후 라즈베리파이에 설치:

```bash
sudo cp ~/uav_ws/src/uav_camera_bringup/systemd/uav-camera.service /etc/systemd/system/uav-camera.service
sudo systemctl daemon-reload
sudo systemctl enable uav-camera.service
sudo systemctl start uav-camera.service
```

로그 확인:

```bash
systemctl status uav-camera.service
journalctl -u uav-camera.service -f
```

## 현재 마일스톤

첫 번째 성공 기준은 다음과 같다:

```text
라즈베리파이가 발행:
  /uav/camera/color/image_raw
  /uav/camera/depth/image_rect_raw
  /uav/camera/color/camera_info
  /uav/camera/depth/camera_info
  /uav/heartbeat

메인 PC가 수신:
  안정적인 FPS의 카메라 이미지
  heartbeat/상태 메시지
  측정 가능한 토픽 대역폭과 레이턴시
```

## Stage 3: 대역폭 절감을 위한 압축 전송

기본 시스템 launch는 이제 Wi-Fi 대역폭을 줄이기 위해 raw `Image` 대신 압축 이미지를
발행하며, 컬러/뎁스 FPS를 각각 독립적으로 조절할 수 있다 (`color_fps` 기본 15,
`depth_fps` 기본 5).

- **컬러**: 이 RealSense 컬러 센서의 V4L2 드라이버는 `YUYV`만 노출한다 — 하드웨어
  MJPG 모드가 없다. `v4l2_mjpeg_node`가 raw YUYV를 캡처해서 OpenCV로 소프트웨어
  JPEG 인코딩(`jpeg_quality` 파라미터, 기본 80)한 뒤 `sensor_msgs/CompressedImage`로
  발행한다.
- **뎁스**: `v4l2_depth_node`에 `publish_raw` / `publish_compressed` 파라미터가
  추가되었다. 기본 system/rgbd launch는 대역폭 절감을 위해 PNG로 압축한 16UC1
  스트림만 발행한다 (`png_compression_level` 파라미터). `publish_raw:=true`로
  설정하면 raw `Image` 발행도 여전히 가능하다.
- 두 `CompressedImage.format` 문자열 모두 `cv_bridge` 규약
  (`"<encoding>; <codec> compressed"`)을 따르므로, 커스텀 OpenCV 코드뿐 아니라
  표준 `image_transport`의 "compressed" 서브스크라이버로도 디코드할 수 있다.
  [메인 PC에서 각 토픽 수신하는 법](#메인-pc에서-각-토픽-수신하는-법) 참고.
- 두 V4L2 노드 모두 이제 백그라운드 스레드로 `v4l2-ctl`의 stderr를 계속 읽어들인다.
  `v4l2-ctl`은 스트리밍 중 fps/드랍 카운트를 실시간으로 stderr에 계속 출력하는데,
  이를 읽어주지 않으면 파이프 버퍼가 가득 차서 약 10~15초 후 스트림이 조용히
  죽어버린다.

**알려진 이슈**: 뎁스 압축 토픽은 안정적으로 동작하지만(크래시 없음), 요청한
`depth_fps:=5.0`에 비해 실측 발행 속도가 ~1.3Hz밖에 안 된다 — 위의 stderr 수정보다는
PNG 인코딩 또는 raw 프레임 읽기 자체의 오버헤드가 Pi CPU에서 병목인 것으로 보이나,
아직 원인을 완전히 특정하지는 못했다.
