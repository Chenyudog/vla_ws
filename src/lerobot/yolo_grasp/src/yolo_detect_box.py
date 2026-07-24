#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import Float32MultiArray
from geometry_msgs.msg import PointStamped
import numpy as np
import cv2
from cv_bridge import CvBridge

class CubeDetectNode(Node):
    def __init__(self):
        super().__init__("cube_detector")
        # 图像转换工具：OpenCV <-> ROS Image
        self.bridge = CvBridge()
        self.rgb_img = None
        self.depth_img = None

        # 订阅RGB彩色图像
        self.sub_rgb = self.create_subscription(
            Image,
            "/camera_sensor/image_raw",
            self.rgb_callback,
            10
        )
        # 订阅深度图像
        self.sub_depth = self.create_subscription(
            Image,
            "/camera_sensor/depth/image_raw",
            self.depth_callback,
            10
        )

        # 发布1：原始检测框数组
        self.pub_detect = self.create_publisher(
            Float32MultiArray,
            "/yolo/detect_info",
            10
        )
        # 发布2：方块中心点像素XY + 深度Z
        self.pub_center = self.create_publisher(
            PointStamped,
            "/cube/center_3d",
            10
        )
        # 发布3：带检测标注的可视化图像（sensor_msgs/msg/Image）
        self.pub_draw_img = self.create_publisher(
            Image,
            "/camera_sensor/detect_image",
            10
        )

    def rgb_callback(self, msg):
        self.rgb_img = np.frombuffer(msg.data, dtype=np.uint8).reshape(msg.height, msg.width, 3)
        self.img_header = msg.header  # 同步原图时间戳、坐标系
        if self.depth_img is None:
            return
        self.detect_cube()

    def depth_callback(self, msg):
        self.depth_img = np.frombuffer(msg.data, dtype=np.float32).reshape(msg.height, msg.width)

    def detect_cube(self):
        draw_img = self.rgb_img.copy()
        det_data = []

        # HSV筛选绿色立方体
        blur = cv2.GaussianBlur(draw_img, (3, 3), 0)
        hsv = cv2.cvtColor(blur, cv2.COLOR_BGR2HSV)
        lower_green = np.array([35, 60, 60])
        upper_green = np.array([77, 255, 255])
        mask = cv2.inRange(hsv, lower_green, upper_green)

        kernel = np.ones((2, 2), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < 30 or area > 3000:
                continue
            approx = cv2.approxPolyDP(cnt, 0.025 * cv2.arcLength(cnt, True), True)
            edge_count = len(approx)
            x, y, w, h = cv2.boundingRect(approx)
            wh_ratio = w / h

            if 4 <= edge_count <= 6 and 0.6 < wh_ratio < 1.4:
                x1 = float(x)
                y1 = float(y)
                x2 = float(x + w)
                y2 = float(y + h)
                det_data.extend([x1, y1, x2, y2, 0.99, 0.0])

                # 绘制标注框和文字
                cv2.rectangle(draw_img, (x, y), (x+w, y+h), (0, 0, 255), 2)
                cv2.putText(draw_img, "Cube", (x, y - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

                # 计算像素中心 + 读取深度
                center_u = int((x1 + x2) / 2)
                center_v = int((y1 + y2) / 2)
                depth_val = float(self.depth_img[center_v, center_u])

                # 发布中心点PointStamped
                center_msg = PointStamped()
                center_msg.header = self.img_header
                center_msg.header.frame_id = "camera_optical_link"
                center_msg.point.x = float(center_u)
                center_msg.point.y = float(center_v)
                center_msg.point.z = depth_val
                self.pub_center.publish(center_msg)
                self.get_logger().info(f"方块中心({center_u},{center_v}) 深度:{depth_val:.3f}m")

        # 1. 发布检测框数组
        pub_msg = Float32MultiArray()
        pub_msg.data = det_data
        self.pub_detect.publish(pub_msg)

        # 2. 将OpenCV图像转为ROS Image消息并发布
        ros_img_msg = self.bridge.cv2_to_imgmsg(draw_img, encoding="bgr8")
        ros_img_msg.header = self.img_header
        self.pub_draw_img.publish(ros_img_msg)

def main():
    rclpy.init()
    node = CubeDetectNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("视觉节点关闭")
    rclpy.shutdown()

if __name__ == "__main__":
    main()