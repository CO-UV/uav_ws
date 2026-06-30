import json
import os
import time

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class SystemMonitorNode(Node):
    def __init__(self):
        super().__init__("system_monitor_node")
        self.declare_parameter("topic", "/uav/system/status")
        self.declare_parameter("rate_hz", 1.0)

        topic = self.get_parameter("topic").value
        self.publisher = self.create_publisher(String, topic, 10)
        self.create_timer(1.0 / float(self.get_parameter("rate_hz").value), self._publish)

        self._last_cpu_total = None
        self._last_cpu_idle = None

    def _publish(self):
        payload = {
            "stamp_unix_sec": time.time(),
            "cpu_percent": self._cpu_percent(),
            "load_average": os.getloadavg(),
            "memory": self._memory_info(),
            "cpu_temperature_c": self._cpu_temperature(),
        }

        msg = String()
        msg.data = json.dumps(payload, sort_keys=True)
        self.publisher.publish(msg)

    def _cpu_percent(self):
        try:
            with open("/proc/stat", "r", encoding="utf-8") as stat_file:
                fields = stat_file.readline().split()[1:]
        except OSError:
            return None

        values = [int(value) for value in fields]
        idle = values[3] + values[4]
        total = sum(values)

        if self._last_cpu_total is None:
            self._last_cpu_total = total
            self._last_cpu_idle = idle
            return None

        total_delta = total - self._last_cpu_total
        idle_delta = idle - self._last_cpu_idle
        self._last_cpu_total = total
        self._last_cpu_idle = idle

        if total_delta <= 0:
            return None
        return 100.0 * (1.0 - idle_delta / total_delta)

    def _memory_info(self):
        info = {}
        try:
            with open("/proc/meminfo", "r", encoding="utf-8") as meminfo:
                for line in meminfo:
                    key, value = line.split(":", 1)
                    if key in ("MemTotal", "MemAvailable"):
                        info[key] = int(value.strip().split()[0]) * 1024
        except OSError:
            return None

        if "MemTotal" in info and "MemAvailable" in info:
            info["MemUsed"] = info["MemTotal"] - info["MemAvailable"]
            info["MemUsedPercent"] = 100.0 * info["MemUsed"] / info["MemTotal"]
        return info

    def _cpu_temperature(self):
        paths = [
            "/sys/class/thermal/thermal_zone0/temp",
            "/sys/class/hwmon/hwmon0/temp1_input",
        ]
        for path in paths:
            try:
                with open(path, "r", encoding="utf-8") as temp_file:
                    return int(temp_file.read().strip()) / 1000.0
            except OSError:
                continue
            except ValueError:
                continue
        return None


def main(args=None):
    rclpy.init(args=args)
    node = SystemMonitorNode()
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
