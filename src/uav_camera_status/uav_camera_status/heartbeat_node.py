import json
import socket
import time

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class HeartbeatNode(Node):
    def __init__(self):
        super().__init__("heartbeat_node")
        self.declare_parameter("topic", "/uav/heartbeat")
        self.declare_parameter("rate_hz", 1.0)
        self.declare_parameter("vehicle_id", "uav_01")

        topic = self.get_parameter("topic").value
        rate_hz = float(self.get_parameter("rate_hz").value)
        self.vehicle_id = self.get_parameter("vehicle_id").value
        self.hostname = socket.gethostname()
        self.sequence = 0
        self.start_time = time.monotonic()

        self.publisher = self.create_publisher(String, topic, 10)
        self.create_timer(1.0 / rate_hz, self._publish)

    def _publish(self):
        now = time.time()
        payload = {
            "vehicle_id": self.vehicle_id,
            "hostname": self.hostname,
            "sequence": self.sequence,
            "stamp_unix_sec": now,
            "uptime_sec": time.monotonic() - self.start_time,
            "ok": True,
        }
        self.sequence += 1

        msg = String()
        msg.data = json.dumps(payload, sort_keys=True)
        self.publisher.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = HeartbeatNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        try:
            node.destroy_node()
        except KeyboardInterrupt:
            pass
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
