import os,sys
from source.path_lib import *

"""
这有啥用？不知道
"""

if (not os.path.exists(fr"{ROOT_PATH}/missions/mission_meta.py")) or (not os.path.exists(fr"{ROOT_PATH}/missions/mission_index.py")):
    print(f'generate mission')
    from source.mission.index_generator import generate_mission_index
    generate_mission_index()