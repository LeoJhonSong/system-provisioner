# -*- coding: utf-8 -*-

import sys
import os
import re
import time


def __len__(str):
    return 20

# colors
OFFSET = '\033[0m'
BLACK_FG = '\033[30m'
RED_FG = '\033[31m'
GREEN_FG = '\033[32m'
YELLOW_FG = '\033[33m'
BLUE_FG = '\033[34m'
PURPLE_FG = '\033[35m'
CYAN_FG = '\033[36m'
WHITE_FG = '\033[37m'
BLACK_BG = '\033[40m'
RED_BG = '\033[41m'
GREEN_BG = '\033[42m'
YELLOW_BG = '\033[43m'
BLUE_BG = '\033[44m'
PURPLE_BG = '\033[45m'
CYAN_BG = '\033[46m'
WHITE_BG = '\033[47m'

# some segments you may want to use
python_version = ' Python ' + ".".join(map(str, sys.version_info[:3]))
python_interpreter_path = '  ' + sys.executable
local_time = ' ' + time.strftime('%H:%M:%S', time.localtime(time.time()))
# the delimiter used at the end of a segment
delimiter = ''
pointer = ' '
# segments of the prompt
prompt = [
    [BLUE_BG, WHITE_FG, python_version],
    [GREEN_BG, WHITE_FG, python_interpreter_path],
    [WHITE_BG, BLACK_FG, local_time]
]

sys.ps1 = OFFSET
for i in range(len(prompt)):
    sys.ps1 = sys.ps1 + prompt[i][0] + prompt[i][1] + ' ' + prompt[i][2]
    sys.ps1 = sys.ps1 + ' ' + OFFSET + re.sub(r'(?<=\033\[)\d', '3', prompt[i][0])
    if i == len(prompt)-1:
        sys.ps1 = sys.ps1 + delimiter
    else:
        sys.ps1 = sys.ps1 + prompt[i+1][0] + delimiter
    sys.ps1 = sys.ps1 + OFFSET

sys.ps1 = sys.ps1 + '\n' + pointer
