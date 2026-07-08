import time

import cv2
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

        # RealSense color sensor only exposes YUYV over V4L2 (no hardware MJPG).
        # Capturing via cv2.VideoCapture (rather than shelling out to v4l2-ctl and
        # parsing a raw byte pipe by hand) lets OpenCV/V4L2 handle frame
        # synchronization — a hand-rolled fixed-size pipe read desyncs from the
        # true frame boundary whenever a buffer is dropped, which silently
        # corrupts every frame afterward (looks like scrambled green/magenta
        # bands, not just a wrong color channel order).
        self.capture = self._open_capture()

        period = 1.0 / self.fps if self.fps > 0 else 1.0 / 15.0
        self.timer = self.create_timer(period, self.publish_frame)
        self.get_logger().info(
            f"Publishing JPEG (software-encoded via cv2.VideoCapture) from "
            f"{self.video_device} as CompressedImage {self.width}x{self.height}@{self.fps:g}"
        )

    def _open_capture(self):
        capture = cv2.VideoCapture(self.video_device, cv2.CAP_V4L2)
        capture.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"YUYV"))
        capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        capture.set(cv2.CAP_PROP_FPS, self.fps)
        capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        if not capture.isOpened():
            raise RuntimeError(f"Failed to open {self.video_device} via cv2.VideoCapture")

        return capture

    def publish_frame(self):
        ok, bgr = self.capture.read()
        if not ok or bgr is None:
            self.get_logger().warning("Failed to read color frame", throttle_duration_sec=2.0)
            return

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

    def destroy_node(self):
        if hasattr(self, "capture"):
            self.capture.release()
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
