import time

import cv2
import numpy as np
import rclpy
from linuxpy.video.device import Device, V4L2Error, VideoCapture
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from sensor_msgs.msg import CameraInfo, CompressedImage, Image
from std_msgs.msg import Header


class V4L2DepthNode(Node):
    def __init__(self):
        super().__init__("v4l2_depth_node")

        self.declare_parameter("video_device", "/dev/video0")
        self.declare_parameter("image_width", 640)
        self.declare_parameter("image_height", 480)
        self.declare_parameter("fps", 30.0)
        self.declare_parameter("frame_id", "uav_realsense_depth_optical_frame")
        self.declare_parameter("image_topic", "/uav/camera/depth/image_rect_raw")
        self.declare_parameter(
            "compressed_image_topic", "/uav/camera/depth/image_rect_raw/compressed"
        )
        self.declare_parameter("camera_info_topic", "/uav/camera/depth/camera_info")
        self.declare_parameter("publish_raw", True)
        self.declare_parameter("publish_compressed", False)
        self.declare_parameter("png_compression_level", 1)

        self.video_device = self.get_parameter("video_device").value
        self.width = int(self.get_parameter("image_width").value)
        self.height = int(self.get_parameter("image_height").value)
        self.fps = float(self.get_parameter("fps").value)
        self.frame_id = self.get_parameter("frame_id").value
        self.publish_raw = bool(self.get_parameter("publish_raw").value)
        self.publish_compressed = bool(self.get_parameter("publish_compressed").value)
        self.png_compression_level = int(self.get_parameter("png_compression_level").value)

        self.image_pub = None
        if self.publish_raw:
            self.image_pub = self.create_publisher(
                Image, self.get_parameter("image_topic").value, 10
            )
        self.compressed_image_pub = None
        if self.publish_compressed:
            self.compressed_image_pub = self.create_publisher(
                CompressedImage,
                self.get_parameter("compressed_image_topic").value,
                10,
            )
        self.info_pub = self.create_publisher(
            CameraInfo, self.get_parameter("camera_info_topic").value, 10
        )

        self.frame_size = self.width * self.height * 2
        self.device, self.capture, self._frames = self._start_stream()

        period = 1.0 / self.fps if self.fps > 0 else 1.0 / 30.0
        self.timer = self.create_timer(period, self.publish_frame)
        self.get_logger().info(
            f"Publishing Z16 depth from {self.video_device} as 16UC1 "
            f"{self.width}x{self.height}@{self.fps:g} "
            f"raw={self.publish_raw} compressed={self.publish_compressed}"
        )

    def _start_stream(self):
        # Captured via V4L2 mmap streaming (linuxpy) instead of shelling out to
        # v4l2-ctl and parsing a raw stdout pipe by hand. Z16 has no in-stream frame
        # boundary markers (unlike MJPEG's SOI/EOI), so a hand-rolled fixed-size pipe
        # read that ever desyncs from the true frame boundary (one dropped/short read
        # at stream start or under buffer pressure) silently corrupts every frame
        # afterward: adjacent pixels' high/low bytes get spliced together, producing
        # a permanent, stable-looking contour/terracing pattern rather than an
        # obvious glitch. VIDIOC_DQBUF guarantees each dequeued buffer is exactly one
        # full frame, so this desync class can't happen here regardless of timing.
        try:
            device = Device(self.video_device)
            device.open()
            capture = VideoCapture(device)
            capture.set_format(self.width, self.height, "Z16 ")
            if self.fps > 0:
                try:
                    capture.set_fps(int(self.fps))
                except (OSError, V4L2Error):
                    pass  # device may not support this exact interval; keep its default
            capture.open()  # allocates/mmaps buffers and starts streaming
        except (OSError, V4L2Error) as exc:
            raise RuntimeError(
                f"Failed to open depth device {self.video_device}: {exc}"
            ) from exc

        return device, capture, iter(capture)

    def publish_frame(self):
        try:
            frame = bytes(next(self._frames))
        except (StopIteration, OSError, V4L2Error) as exc:
            self.get_logger().error(f"Depth capture stream stopped: {exc}")
            self.timer.cancel()
            return

        if len(frame) != self.frame_size:
            self.get_logger().warning("Failed to read depth frame", throttle_duration_sec=2.0)
            return

        header = Header()
        header.stamp = self.get_clock().now().to_msg()
        header.frame_id = self.frame_id

        # Building a full Image message (with `data` set to the 600KB+ raw frame)
        # costs ~0.5s on this Pi even when it's never published — rclpy's array-field
        # setter is that slow for a buffer this size. Only pay for it when actually
        # publishing raw, instead of doing it unconditionally every frame.
        if self.image_pub is not None:
            image = Image()
            image.header = header
            image.height = self.height
            image.width = self.width
            image.encoding = "16UC1"
            image.is_bigendian = 0
            image.step = self.width * 2
            image.data = frame
            self.image_pub.publish(image)

        if self.compressed_image_pub is not None:
            depth = np.frombuffer(frame, dtype=np.uint16).reshape(self.height, self.width)
            ok, encoded = cv2.imencode(
                ".png",
                depth,
                [cv2.IMWRITE_PNG_COMPRESSION, self.png_compression_level],
            )
            if ok:
                compressed = CompressedImage()
                compressed.header = header
                compressed.format = "16UC1; png compressed"
                compressed.data = encoded.tobytes()
                self.compressed_image_pub.publish(compressed)
            else:
                self.get_logger().warning(
                    "Failed to encode depth frame as PNG",
                    throttle_duration_sec=2.0,
                )

        info = CameraInfo()
        info.header = header
        info.height = self.height
        info.width = self.width
        self.info_pub.publish(info)

    def destroy_node(self):
        if hasattr(self, "capture"):
            self.capture.close()
        if hasattr(self, "device"):
            self.device.close()
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
