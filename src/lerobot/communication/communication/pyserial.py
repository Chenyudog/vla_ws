import serial
import time
import logging
from serial.tools import list_ports
import rclpy
from rclpy.node import Node

# 配置日志输出
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class TTYACMReceiverNode(Node):
    def __init__(self):
        super().__init__('ttyacm_receiver_node')
        
        # 串口参数
        self.declare_parameter('port', '/dev/ttySTM32F4')
        self.declare_parameter('baudrate', 115200)
        self.declare_parameter('timeout', 1.0)
        
        self.port = self.get_parameter('port').value
        self.baudrate = self.get_parameter('baudrate').value
        self.timeout = self.get_parameter('timeout').value
        
        self.serial_conn = None
        self.is_connected = False
        self.receive_thread = None
        self.running = False

    def setup_permissions(self):
        """确保用户有权限访问串口设备"""
        try:
            import os
            # 检查当前用户是否在dialout组中
            if 'dialout' not in os.popen('groups').read():
                self.get_logger().warning("当前用户不在dialout组，可能无法访问串口")
                self.get_logger().info("请运行: sudo usermod -a -G dialout $USER，然后重新登录")
        except Exception as e:
            self.get_logger().warning(f"检查权限时出错: {str(e)}")

    def connect(self):
        """建立与ttyACM0的连接"""
        # 先检查权限
        self.setup_permissions()
        
        try:
            # 检查端口是否存在
            available_ports = [p.device for p in list_ports.comports()]
            if self.port not in available_ports:
                self.get_logger().error(f"设备 {self.port} 不存在，可用设备: {available_ports}")
                return False

            # 初始化串口连接
            self.serial_conn = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                bytesize=serial.EIGHTBITS,
                timeout=self.timeout
            )

            if self.serial_conn.is_open:
                self.is_connected = True
                self.get_logger().info(f"成功连接到 {self.port}，波特率: {self.baudrate}")
                return True
            return False

        except serial.SerialException as e:
            self.get_logger().error(f"串口连接失败: {str(e)}")
            return False
        except Exception as e:
            self.get_logger().error(f"连接时发生错误: {str(e)}")
            return False

    def receive_data(self):
        """接收数据的线程函数"""
        if not self.is_connected or not self.serial_conn:
            self.get_logger().error("未建立连接,请先调用connect()方法")
            return

        try:
            self.get_logger().info("开始接收数据...")
            self.running = True
            
            while self.running and rclpy.ok():
                # 读取一行数据
                data = self.serial_conn.readline()
                if data:
                    # 尝试解码为字符串
                    try:
                        decoded_data = data.decode('utf-8').strip()
                        self.get_logger().info(f"接收到数据: {decoded_data}")
                        # 在这里你可以添加ROS 2发布数据的代码
                    except UnicodeDecodeError:
                        # 如果无法解码，显示原始字节数据
                        self.get_logger().info(f"接收到二进制数据: {data.hex()}")
                time.sleep(0.001)  # 短暂延时

        except serial.SerialException as e:
            self.get_logger().error(f"接收数据时出错: {str(e)}")
        finally:
            self.disconnect()

    def disconnect(self):
        """断开串口连接"""
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()
            self.is_connected = False
            self.get_logger().info(f"已断开与 {self.port} 的连接")

    def run(self):
        """运行节点"""
        if self.connect():
            self.receive_data()
        else:
            self.get_logger().error("无法建立连接，程序退出")

def main(args=None):
    rclpy.init(args=args)
    
    try:
        node = TTYACMReceiverNode()
        node.run()
    except KeyboardInterrupt:
        node.get_logger().info("用户中断程序")
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == "__main__":
    main()
