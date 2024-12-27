from source.interaction.interaction_core import itt
from source.api.pdocr_complete import ocr
from datetime import datetime, timedelta
import math

from source.ui import page

class IngameTime:

    def __init__(self, center=(1440, 503), radius=100):
        self.center = center
        self.radius = radius

    def _calculate_pointer_position(self,time):
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
        x_offset = -self.radius * math.sin(pointer_radian)
        y_offset = self.radius * math.cos(pointer_radian)
        
        # 根据圆心坐标计算实际指针位置
        x = round(self.center[0] + x_offset)
        y = round(self.center[1] + y_offset)
        
        return (x, y), pointer_angle

    def _get_mouse_positions(self,cur_time, tar_time, after_24hour=False):
        """生成鼠标移动路径以调整时钟指针从当前时间到目标时间。

        Args:
            cur_time (str): 当前时间，格式为"%H:%M"。
            tar_time (str): 目标时间，格式为"%H:%M"。
            after_24hour (bool, optional): 是否先转一整圈再调整，默认为False。

        Returns:
            list: 鼠标需要移动到的坐标列表。
        """
        steps = []
        if after_24hour:
            tar_time_for_24h=(datetime.strptime(cur_time, "%H:%M") - timedelta(minutes=1)).strftime("%H:%M")
            steps = self._get_mouse_positions(cur_time, tar_time_for_24h, False)
        
        # 获取当前和目标时间的指针位置及角度
        cur_pos, current_angle = self._calculate_pointer_position(cur_time)
        _, target_angle = self._calculate_pointer_position(tar_time)
        
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
            new_pos, _ = self._calculate_pointer_position(time_str)
            steps.append(new_pos)
        
        # 确保最后一步到达目标位置
        if len(steps) > 0 and steps[-1][1] != target_angle:
            steps.append(self._calculate_pointer_position(tar_time)[0])
        
        return steps
    def get_cur_time(self):
        """获取游戏内当前时间。"""
        return ocr.get_all_texts(itt.capture(posi=[900,400,1050,450]))[0]

    def set_time(self,tar_time, after_24hour=False):
        """调整时钟指针从当前时间到目标时间。

        Args:
            tar_time (str): 目标时间，格式为"%H:%M"。
            after_24hour (bool, optional): 是否先转一整圈再调整，默认为False。
            center (tuple, optional): 表盘中心点坐标，默认为(1440, 503)。
            radius (int, optional): 指针长度，默认为100。
        """
        cur_time = self.get_cur_time()
        pois = self._get_mouse_positions(cur_time, tar_time, after_24hour)
        # 调整时钟指针来调整时间
        for r in range(len(pois) - 1):
            x1, y1 = pois[r]
            x2, y2 = pois[r + 1]

            itt.move_to(x1, y1)
            itt.left_down()
            
            itt.move_to(x2, y2)
            itt.delay(0.5)

            itt.left_up()
            itt.delay(0.5)
        
        # 确认修改时间 按钮
        itt.move_to(1324, 1018)
        itt.left_click()
        
        #镜头提升的动画时间
        itt.delay(2) 

        # 等待时间调整完成(时间不再变化)
        while not cur_time == self.get_cur_time():
            cur_time = self.get_cur_time()
            itt.delay(1)
        
        #镜头回落的动画时间
        itt.delay(2) 

    def set_daylight(self):
        """调到白天"""
        self.set_time("11:00")

    def set_night(self):
        """调到晚上"""
        self.set_time("23:00")

    def set_as_tomorrow(self):
        """调到明天"""
        self.set_time("00:00")

    def set_as_2days_later(self):
        """调到后天"""
        self.set_time("00:00", after_24hour=True)

if __name__ == "__main__":
    from source.ui.ui import ui_control
    import source.ui.page as UIPage

    ui_control.ui_goto(UIPage.page_time)

    IGT=IngameTime()
    IGT.set_as_tomorrow()
    print('done')
    IGT.set_time("12:00")

    ui_control.ui_goto(UIPage.page_main)