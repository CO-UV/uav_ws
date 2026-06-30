import os

import cv2
import rclpy
from cv_bridge import CvBridge
from rclpy.node import Node
from sensor_msgs.msg import Image


class SaveImageOnce(Node):
    def __init__(self):
        super().__init__("save_image_once")

        self.declare_parameter("image_topic", "/uav/camera/color/image_raw")
        self.declare_parameter("output_path", "/tmp/uav_color_snapshot.jpg")
        self.declare_parameter("encoding", "bgr8")

        self.image_topic = self.get_parameter("image_topic").value
        self.output_path = self.get_parameter("output_path").value
        self.encoding = self.get_parameter("encoding").value
        self.bridge = CvBridge()
        self.done = False
        self.exit_code = 0

        self.subscription = self.create_subscription(Image, self.image_topic, self._on_image, 10)
        self.get_logger().info(f"Waiting for one image on {self.image_topic}")

    def _on_image(self, msg):
        try:
            image = self.bridge.imgmsg_to_cv2(msg, desired_encoding=self.encoding)
        except Exception as exc:
            self.get_logger().error(f"Failed to convert image: {exc}")
            self.exit_code = 1
            self.done = True
            return

        directory = os.path.dirname(self.output_path)
        if directory:
            os.makedirs(directory, exist_ok=True)

        if not cv2.imwrite(self.output_path, image):
            self.get_logger().error(f"Failed to write image: {self.output_path}")
            self.exit_code = 1
            self.done = True
            return

        self.get_logger().info(
            f"Saved {msg.width}x{msg.height} frame_id={msg.header.frame_id} to {self.output_path}"
        )
        self.done = True


def main(args=None):
    rclpy.init(args=args)
    node = SaveImageOnce()
    try:
        while rclpy.ok() and not node.done:
            rclpy.spin_once(node, timeout_sec=0.1)
        return node.exit_code
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
