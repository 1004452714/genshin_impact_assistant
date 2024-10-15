from source.interaction.interaction_core import itt
from source.api.pdocr_complete import ocr
from datetime import datetime
import math

def calculate_pointer_position(time, center=(1440, 503), radius=100):
    """根据给定的时间计算指针在表盘上的位置。

    Args:
        time (str): 时间字符串，格式为 "%H:%M"。
        center (tuple, optional): 表盘中心点坐标，默认为(1440, 503)。
        radius (int, optional): 指针半径长度，默认为100。

    Returns:
        tuple: 指针位置坐标(x, y) 和相对于12点的角度。
    """
    # 解析时间并转换成角度
    parsed_time = datetime.strptime(time, "%H:%M").time()
    pointer_angle = parsed_time.hour * 15.0 + parsed_time.minute * 0.25
    
    # 将角度转换为弧度
    pointer_radian = math.radians(pointer_angle)
    
    # 计算指针相对于圆心的偏移量
    x_offset = -radius * math.sin(pointer_radian)
    y_offset = radius * math.cos(pointer_radian)
    
    # 根据圆心坐标计算实际指针位置
    x = round(center[0] + x_offset)
    y = round(center[1] + y_offset)
    
    return (x, y), pointer_angle

def get_mouse_positions(cur_time, tar_time, after_24hour=False, center=(1440, 503), radius=100):
    """生成鼠标移动路径以调整时钟指针从当前时间到目标时间。

    Args:
        cur_time (str): 当前时间，格式为"%H:%M"。
        tar_time (str): 目标时间，格式为"%H:%M"。
        after_24hour (bool, optional): 是否先转一整圈再调整，默认为False。
        center (tuple, optional): 表盘中心点坐标，默认为(1440, 503)。
        radius (int, optional): 指针半径长度，默认为100。

    Returns:
        list: 鼠标移动步骤列表。
    """
    steps = []
    if after_24hour:
        steps = get_mouse_positions(cur_time, "12:00", False, center, radius)
    
    # 获取当前和目标时间的指针位置及角度
    cur_pos, current_angle = calculate_pointer_position(cur_time, center, radius)
    _, target_angle = calculate_pointer_position(tar_time, center, radius)
    
    # 计算需要旋转的角度差
    angle_diff = (target_angle - current_angle) % 360
    
    # 确定是否需要分步移动
    if angle_diff > 160:
        num_steps = int(math.ceil(angle_diff / 160.0))
        step_angle = angle_diff / num_steps
    else:
        num_steps = 1
        step_angle = angle_diff
    
    # 添加初始位置到步骤列表
    steps.append(cur_pos)
    
    # 生成中间位置
    for i in range(num_steps):
        new_angle = current_angle + (i + 1) * step_angle
        if new_angle >= 360:
            new_angle -= 360
        hours_decimal = new_angle / 15
        time_str = f"{int(hours_decimal):02d}:{int((hours_decimal - int(hours_decimal)) * 60):02d}"
        new_pos, _ = calculate_pointer_position(time_str, center, radius)
        steps.append(new_pos)
    
    # 确保最后一步到达目标位置
    if len(steps) > 0 and steps[-1][1] != target_angle:
        steps.append(calculate_pointer_position(tar_time, center, radius)[0])
    
    return steps

if __name__ == "__main__":
    # 截图识别当前时间
    cur_time = ocr.get_all_texts(itt.capture(posi=[900,400,1050,450]))[0]
    
    # 获取调整时间需要鼠标移动的路径
    result = get_mouse_positions(cur_time, '12:00', after_24hour=True)
    
    # 执行鼠标移动
    for r in range(len(result) - 1):
        x1, y1 = result[r]
        x2, y2 = result[r + 1]

        itt.move_to(x=x1, y=y1)
        itt.left_down()
        # print(f'{x1},{y1} 按下')
        
        itt.move_to(x=x2, y=y2)
        itt.delay(0.5)
        itt.left_up()
        # print(f'{x2},{y2} 释放')

        itt.delay(0.5)