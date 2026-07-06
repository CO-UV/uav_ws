import subprocess
import threading
import time

import cv2
import numpy as np
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from sensor_msgs.msg import CameraInfo, CompressedImage


class V4L2MjpegNode(Node):
    def __init__(self):
        super().__init__("v4l2_mjpeg_node")

        self.declare_parameter("video_device", "/dev/video4")
        self.declare_parameter("image_width", 640)
        self.declare_parameter("image_height", 480)
        self.declare_parameter("fps", 15.0)
        self.declare_parameter("frame_id", "uav_realsense_color_optical_frame")
        self.declare_parameter(
            "image_topic", "/uav/camera/color/image_raw/compressed"
        )
        self.declare_parameter("camera_info_topic", "/uav/camera/color/camera_info")
        self.declare_parameter("jpeg_quality", 80)

        self.video_device = self.get_parameter("video_device").value
        self.width = int(self.get_parameter("image_width").value)
        self.height = int(self.get_parameter("image_height").value)
        self.fps = float(self.get_parameter("fps").value)
        self.frame_id = self.get_parameter("frame_id").value
        self.jpeg_quality = int(self.get_parameter("jpeg_quality").value)

        self.image_pub = self.create_publisher(
            CompressedImage, self.get_parameter("image_topic").value, 10
        )
        self.info_pub = self.create_publisher(
            CameraInfo, self.get_parameter("camera_info_topic").value, 10
        )

        # RealSense color sensor only exposes YUYV over V4L2 (no hardware MJPG),
        # so JPEG compression is done in software from the raw YUYV frame.
        self.frame_size = self.width * self.height * 2
        self.stream = self._start_stream()

        period = 1.0 / self.fps if self.fps > 0 else 1.0 / 15.0
        self.timer = self.create_timer(period, self.publish_frame)
        self.get_logger().info(
            f"Publishing JPEG (software-encoded from YUYV) from {self.video_device} "
            f"as CompressedImage {self.width}x{self.height}@{self.fps:g}"
        )

    def _start_stream(self):
        command = [
            "v4l2-ctl",
            f"--device={self.video_device}",
            f"--set-fmt-video=width={self.width},height={self.height},pixelformat=YUYV",
            f"--set-parm={int(self.fps)}",
            "--stream-mmap",
            "--stream-to=-",
        ]
        try:
            stream = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=0,
            )
        except FileNotFoundError as exc:
            raise RuntimeError("v4l2-ctl is required. Install v4l-utils.") from exc

        self._stderr_tail = b""
        self._stderr_lock = threading.Lock()
        self._stderr_thread = threading.Thread(
            target=self._drain_stderr, args=(stream,), daemon=True
        )
        self._stderr_thread.start()

        time.sleep(0.1)
        if stream.poll() is not None:
            raise RuntimeError(
                f"v4l2-ctl failed to start color stream: {self._read_stream_error()}"
            )

        return stream

    def publish_frame(self):
        if self.stream.poll() is not None:
            self.get_logger().error(
                f"v4l2-ctl color stream stopped: {self._read_stream_error()}"
            )
            self.timer.cancel()
            return

        frame = self._read_exact_frame()
        if len(frame) != self.frame_size:
            self.get_logger().warning("Failed to read color frame", throttle_duration_sec=2.0)
            return

        yuyv = np.frombuffer(frame, dtype=np.uint8).reshape(self.height, self.width, 2)
        bgr = cv2.cvtColor(yuyv, cv2.COLOR_YUV2BGR_YUYV)
        ok, encoded = cv2.imencode(
            ".jpg", bgr, [cv2.IMWRITE_JPEG_QUALITY, self.jpeg_quality]
        )
        if not ok:
            self.get_logger().warning(
                "Failed to encode color frame as JPEG", throttle_duration_sec=2.0
            )
            return

        stamp = self.get_clock().now().to_msg()

        image = CompressedImage()
        image.header.stamp = stamp
        image.header.frame_id = self.frame_id
        image.format = "bgr8; jpeg compressed"
        image.data = encoded.tobytes()
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

    def _drain_stderr(self, stream):
        while True:
            chunk = stream.stderr.read(4096)
            if not chunk:
                return
            with self._stderr_lock:
                self._stderr_tail = (self._stderr_tail + chunk)[-4096:]

    def _read_stream_error(self):
        with self._stderr_lock:
            tail = self._stderr_tail
        if not tail:
            return "no error output"
        return tail.decode(errors="replace").strip()

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
        node = V4L2MjpegNode()
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
