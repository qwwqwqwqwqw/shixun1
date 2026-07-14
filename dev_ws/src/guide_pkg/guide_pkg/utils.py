"""辅助函数：坐标加载、状态转换、四元数计算等。

B组长使用的函数：
  - load_classrooms(path)    → (classrooms, origin)
  - get_room_coord(classrooms, room, door='front') → (x, y, yaw) or None
  - load_face_room_map(path) → dict {person_name: room_number}
  - make_pose_stamped(x, y, yaw) → geometry_msgs/PoseStamped
"""
import math
import yaml
from builtin_interfaces.msg import Time
from geometry_msgs.msg import PoseStamped


def load_classrooms(yaml_path):
    """加载 classrooms.yaml → (教室坐标字典, 起点坐标)。"""
    with open(yaml_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f) or {}
    classrooms = data.get('classrooms', {})
    origin = data.get('origin', None)
    return classrooms, origin


def get_room_coord(classrooms, room_number, door='front'):
    """获取教室坐标，兼容 front/back 新格式和 x/y/yaw 旧格式。
    
    新格式: {room: {front: {x,y,yaw}, back: {x,y,yaw}}}
    旧格式: {room: {x, y, yaw}}
    返回 (x, y, yaw) 或 None。
    """
    entry = classrooms.get(room_number)
    if entry is None:
        return None

    # 新格式：有 front/back 子字典
    if 'front' in entry or 'back' in entry:
        door_entry = entry.get(door, entry.get('front', {}))
        if not door_entry:
            return None
        return (door_entry['x'], door_entry['y'], door_entry.get('yaw', 0.0))

    # 旧格式：直接 x/y/yaw
    if 'x' in entry:
        return (entry['x'], entry['y'], entry.get('yaw', 0.0))

    return None


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
