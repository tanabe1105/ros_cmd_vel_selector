from example_interfaces.srv import AddTwoInts

import rclpy
from rclpy.node import Node
import time

from std_msgs.msg import String
from geometry_msgs.msg import Twist



class cmd_vel_selector(Node):

    def __init__(self):
        super().__init__('cmd_vel_selector')
        # "STAND BY" or "GO"
        # "STAND BY"で0,0,0しかでないように、"GO"で普通にcmd_velが出るように
        self.mode_ready = "STAND BY"
        self.mode_ready_sub = self.create_subscription(String, '/mode_ready', self.mode_ready_callback, 10)
        
        
        # 出力先
        self.cmd_vel_uart_pub = self.create_publisher(Twist, '/cmd_vel_uart', 10)
        
        # 現在購読しているsubscriber（最初は None） 
        self.current_sub = None 
        self.current_topic = None

        self.vel = Twist() 
        # self.vel.linear.x = 0.0
        # self.vel.linear.y = 0.0
        # self.vel.angular.z = 0.0
        
        # 値が更新されていなかったとき、すべて0のTwistを出す
        self.zero_twist = Twist()
        # 監視周期は0.1秒
        self.create_timer(0.1, self.watch_timer)
        self.target_timer = time.time() # current_velがpubされているか
        self.twist_timer = time.time() # twistがpubされているか
        # それぞれの値が変化しているか
        self.target_flag = False
        self.twist_flag = False
        
        # どの値をcmd_vel_uartに流すか
        self.target_sub = self.create_subscription(String, '/current_vel', self.target_selecter_callback, 10)
    
    def mode_ready_callback(self, msg):
        if(msg.data == "GO"):
            self.mode_ready = "GO"
        else:
            self.mode_ready = "STAND BY"

    def target_selecter_callback(self, msg): 
        new_topic = msg.data.strip() 
        self.target_timer = time.time()
        
        if new_topic == self.current_topic:
            # self.get_logger().info("読み取るtopicは変化していません")
            return
        
        # 古いsubscriberを破棄
        if self.current_sub is not None:
            self.destroy_subscription(self.current_sub)
            self.get_logger().info(f"古いtopic購読を解除: {self.current_topic}")

        # 新しいトピックを購読
        self.current_sub = self.create_subscription(Twist, new_topic, self.cmd_vel_selector_callback, 10) 
        self.current_topic = new_topic
        self.get_logger().info(f"topic:{new_topic} ") # 新しいトピックを購読 
        self.twist_timer = time.time()

    def cmd_vel_selector_callback(self, msg):
        self.twist_timer = time.time()
        
        # self.vel.linear.x = msg.linear.x
        # self.vel.linear.y = msg.linear.y
        # self.vel.angular.z = msg.angular.z
        if(self.mode_ready == "GO"):
            self.cmd_vel_uart_pub.publish(msg)
            self.get_logger().info(f'MODE = \"GO\", Lx={msg.linear.x} Ly={msg.linear.y} Az={msg.angular.z}')
        else:
            self.cmd_vel_uart_pub.publish(self.zero_twist)
            self.get_logger().info(f'MODE = \"STAND BY\"')
            self.get_logger().info(f'Receiving: Lx={msg.linear.x} Ly={msg.linear.y} Az={msg.angular.z}')

    def watch_timer(self):
        now = time.time()
        
        # 前回の結果を保持
        pre_target_flag = self.target_flag
        # 停止のための変数
        self.target_flag = (now - self.target_timer < 0.9)
        self.twist_flag = (now - self.twist_timer < 0.9)
        
        # target_flagがTrueからFalseに変わった場合、購読を解除
        if pre_target_flag and not self.target_flag:
            if self.current_sub is not None:
                self.destroy_subscription(self.current_sub)
                self.get_logger().info(f"/current_velタイムアウト - topic購読を解除: {self.current_topic}")
                self.current_sub = None
                self.current_topic = None
        
        if self.mode_ready == "STAND BY":
            self.get_logger().info("STAND BY状態のため、cmd_vel_uartは送信されません。")
            self.cmd_vel_uart_pub.publish(self.zero_twist) 
        elif (self.target_flag == False) or (self.twist_flag == False):
            self.get_logger().info("入力が検知されませんでした") 
            # self.get_logger().info('Lx=0.0 Ly=0.0 Az=0.0')
            self.cmd_vel_uart_pub.publish(self.zero_twist) 

def main():
    rclpy.init()

    node = cmd_vel_selector()

    rclpy.spin(node)

    rclpy.shutdown()


if __name__ == '__main__':
    main()

