import json
import time

import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from sensor_msgs.msg import CameraInfo, Image
from std_msgs.msg import String


class CameraHealthNode(Node):
    def __init__(self):
        super().__init__("camera_health_node")

        self.declare_parameter("image_topic", "/uav/camera/color/image_raw")
        self.declare_parameter("camera_info_topic", "/uav/camera/color/camera_info")
        self.declare_parameter("status_topic", "/uav/camera/status")
        self.declare_parameter("timeout_sec", 2.0)
        self.declare_parameter("publish_rate_hz", 1.0)

        self.image_topic = self.get_parameter("image_topic").value
        self.camera_info_topic = self.get_parameter("camera_info_topic").value
        status_topic = self.get_parameter("status_topic").value
        self.timeout_sec = float(self.get_parameter("timeout_sec").value)
        publish_rate_hz = float(self.get_parameter("publish_rate_hz").value)

        self.last_frame_time = None
        self.last_frame_stamp = None
        self.last_camera_info_time = None
        self.last_camera_info_stamp = None
        self.frame_count = 0
        self.camera_info_count = 0
        self.last_report_time = time.monotonic()
        self.last_report_count = 0

        self.create_subscription(Image, self.image_topic, self._on_image, 10)
        self.create_subscription(CameraInfo, self.camera_info_topic, self._on_camera_info, 10)
        self.publisher = self.create_publisher(String, status_topic, 10)
        self.create_timer(1.0 / publish_rate_hz, self._publish_status)

        self.get_logger().info(f"Monitoring camera topic: {self.image_topic}")
        self.get_logger().info(f"Monitoring camera info topic: {self.camera_info_topic}")

    def _on_image(self, msg):
        self.last_frame_time = time.monotonic()
        self.last_frame_stamp = self._stamp_to_float(msg.header.stamp)
        self.frame_count += 1
        self.last_width = msg.width
        self.last_height = msg.height
        self.last_encoding = msg.encoding

    def _on_camera_info(self, msg):
        self.last_camera_info_time = time.monotonic()
        self.last_camera_info_stamp = self._stamp_to_float(msg.header.stamp)
        self.camera_info_count += 1
        self.last_camera_info_width = msg.width
        self.last_camera_info_height = msg.height
        self.last_camera_name = msg.header.frame_id

    def _publish_status(self):
        now = time.monotonic()
        age = None if self.last_frame_time is None else now - self.last_frame_time
        info_age = None if self.last_camera_info_time is None else now - self.last_camera_info_time
        ok = age is not None and age <= self.timeout_sec

        elapsed = max(now - self.last_report_time, 1e-6)
        frames = self.frame_count - self.last_report_count
        fps = frames / elapsed

        payload = {
            "ok": ok,
            "image_topic": self.image_topic,
            "last_frame_age_sec": age,
            "last_frame_stamp_sec": self.last_frame_stamp,
            "camera_info_ok": info_age is not None and info_age <= self.timeout_sec,
            "last_camera_info_age_sec": info_age,
            "last_camera_info_stamp_sec": self.last_camera_info_stamp,
            "camera_info_count": self.camera_info_count,
            "frame_count": self.frame_count,
            "estimated_fps": fps,
            "width": getattr(self, "last_width", None),
            "height": getattr(self, "last_height", None),
            "encoding": getattr(self, "last_encoding", None),
            "camera_info_width": getattr(self, "last_camera_info_width", None),
            "camera_info_height": getattr(self, "last_camera_info_height", None),
            "camera_frame_id": getattr(self, "last_camera_name", None),
        }

        self.last_report_time = now
        self.last_report_count = self.frame_count

        msg = String()
        msg.data = json.dumps(payload, sort_keys=True)
        self.publisher.publish(msg)

    def _stamp_to_float(self, stamp):
        return float(stamp.sec) + float(stamp.nanosec) * 1e-9


def main(args=None):
    rclpy.init(args=args)
    node = CameraHealthNode()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    except RuntimeError:
        if rclpy.ok():
            raise
    finally:
        try:
            node.destroy_node()
        except Exception:
            pass
        try:
            if rclpy.ok():
                rclpy.shutdown()
        except Exception:
            pass


if __name__ == "__main__":
    main()
