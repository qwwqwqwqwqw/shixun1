"""辅助函数：坐标加载、状态转换、四元数计算等。

B组长使用的函数：
  - load_classrooms(path)    → dict {room_number: {x, y, yaw}}
  - load_face_room_map(path) → dict {person_name: room_number}
  - make_pose_stamped(x, y, yaw) → geometry_msgs/PoseStamped
"""
import math
import yaml
from builtin_interfaces.msg import Time
from geometry_msgs.msg import PoseStamped


def load_classrooms(yaml_path):
    """从 classrooms.yaml 加载教室号 → 坐标映射。"""
    with open(yaml_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    return data.get('classrooms', {}) if data else {}


def load_face_room_map(yaml_path):
    """从 face_room_map.yaml 加载 人脸名 → 房间号映射。"""
    with open(yaml_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    return data.get('face_room_map', {}) if data else {}


def yaw_to_quaternion(yaw):
    """欧拉角 yaw → 四元数 (x, y, z, w)"""
    return (0.0, 0.0, math.sin(yaw / 2.0), math.cos(yaw / 2.0))


def make_pose_stamped(frame_id, x, y, yaw):
    """构造 Nav2 目标位姿 PoseStamped。"""
    pose = PoseStamped()
    pose.header.frame_id = frame_id
    pose.pose.position.x = float(x)
    pose.pose.position.y = float(y)
    pose.pose.position.z = 0.0
    qx, qy, qz, qw = yaw_to_quaternion(yaw)
    pose.pose.orientation.x = qx
    pose.pose.orientation.y = qy
    pose.pose.orientation.z = qz
    pose.pose.orientation.w = qw
    return pose
