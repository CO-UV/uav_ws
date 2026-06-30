import subprocess
import time

import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from sensor_msgs.msg import CameraInfo, Image


class V4L2DepthNode(Node):
    def __init__(self):
        super().__init__("v4l2_depth_node")

        self.declare_parameter("video_device", "/dev/video0")
        self.declare_parameter("image_width", 640)
        self.declare_parameter("image_height", 480)
        self.declare_parameter("fps", 30.0)
        self.declare_parameter("frame_id", "uav_realsense_depth_optical_frame")
        self.declare_parameter("image_topic", "/uav/camera/depth/image_rect_raw")
        self.declare_parameter("camera_info_topic", "/uav/camera/depth/camera_info")

        self.video_device = self.get_parameter("video_device").value
        self.width = int(self.get_parameter("image_width").value)
        self.height = int(self.get_parameter("image_height").value)
        self.fps = float(self.get_parameter("fps").value)
        self.frame_id = self.get_parameter("frame_id").value

        self.image_pub = self.create_publisher(
            Image, self.get_parameter("image_topic").value, 10
        )
        self.info_pub = self.create_publisher(
            CameraInfo, self.get_parameter("camera_info_topic").value, 10
        )

        self.frame_size = self.width * self.height * 2
        self.stream = self._start_stream()

        period = 1.0 / self.fps if self.fps > 0 else 1.0 / 30.0
        self.timer = self.create_timer(period, self.publish_frame)
        self.get_logger().info(
            f"Publishing Z16 depth from {self.video_device} as 16UC1 "
            f"{self.width}x{self.height}@{self.fps:g}"
        )

    def _start_stream(self):
        command = [
            "v4l2-ctl",
            f"--device={self.video_device}",
            f"--set-fmt-video=width={self.width},height={self.height},pixelformat=Z16 ",
            f"--set-parm={int(self.fps)}",
            "--stream-mmap",
            "--stream-to=-",
        ]
        try:
            return subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                bufsize=0,
            )
        except FileNotFoundError as exc:
            raise RuntimeError("v4l2-ctl is required. Install v4l-utils.") from exc

    def publish_frame(self):
        if self.stream.poll() is not None:
            self.get_logger().error("v4l2-ctl depth stream stopped")
            self.timer.cancel()
            return

        frame = self._read_exact_frame()
        if len(frame) != self.frame_size:
            self.get_logger().warning("Failed to read depth frame", throttle_duration_sec=2.0)
            return

        stamp = self.get_clock().now().to_msg()

        image = Image()
        image.header.stamp = stamp
        image.header.frame_id = self.frame_id
        image.height = self.height
        image.width = self.width
        image.encoding = "16UC1"
        image.is_bigendian = 0
        image.step = self.width * 2
        image.data = frame
        self.image_pub.publish(image)

        info = CameraInfo()
        info.header = image.header
        info.height = self.height
        info.width = self.width
        self.info_pub.publish(info)

    def _read_exact_frame(self):
        chunks = []
        remaining = self.frame_size
        while remaining > 0:
            chunk = self.stream.stdout.read(remaining)
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        return b"".join(chunks)

    def destroy_node(self):
        if hasattr(self, "stream") and self.stream.poll() is None:
            self.stream.terminate()
            try:
                self.stream.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                self.stream.kill()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = None
    try:
        node = V4L2DepthNode()
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    except RuntimeError:
        if rclpy.ok():
            raise
    finally:
        if node is not None:
            try:
                node.destroy_node()
            except Exception:
                pass
        try:
            if rclpy.ok():
                rclpy.shutdown()
        except Exception:
            pass
        time.sleep(0.1)


if __name__ == "__main__":
    main()
