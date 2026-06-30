import json
import socket
import subprocess
import time

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class NetworkMonitorNode(Node):
    def __init__(self):
        super().__init__("network_monitor_node")
        self.declare_parameter("topic", "/uav/network/status")
        self.declare_parameter("rate_hz", 1.0)
        self.declare_parameter("interface", "wlan0")
        self.declare_parameter("ping_host", "8.8.8.8")

        topic = self.get_parameter("topic").value
        self.interface = self.get_parameter("interface").value
        self.ping_host = self.get_parameter("ping_host").value

        self.publisher = self.create_publisher(String, topic, 10)
        self.create_timer(1.0 / float(self.get_parameter("rate_hz").value), self._publish)

    def _publish(self):
        payload = {
            "stamp_unix_sec": time.time(),
            "hostname": socket.gethostname(),
            "interface": self.interface,
            "ip_address": self._ip_address(),
            "ping_host": self.ping_host,
            "ping_ok": self._ping_ok(),
        }

        msg = String()
        msg.data = json.dumps(payload, sort_keys=True)
        self.publisher.publish(msg)

    def _ip_address(self):
        try:
            result = subprocess.run(
                ["ip", "-4", "addr", "show", self.interface],
                check=False,
                capture_output=True,
                text=True,
                timeout=0.5,
            )
        except Exception:
            return None

        for line in result.stdout.splitlines():
            line = line.strip()
            if line.startswith("inet "):
                return line.split()[1]
        return None

    def _ping_ok(self):
        try:
            result = subprocess.run(
                ["ping", "-c", "1", "-W", "1", self.ping_host],
                check=False,
                capture_output=True,
                text=True,
                timeout=1.5,
            )
            return result.returncode == 0
        except Exception:
            return False


def main(args=None):
    rclpy.init(args=args)
    node = NetworkMonitorNode()
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
