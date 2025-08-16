# -*- coding: utf-8 -*-

import sys
import os
import re
import time

def wrap_ansi(text):
    """Wrap ANSI escape sequences with readline markers to make them invisible for length calculation"""
    return '\001' + text + '\002'

# colors with readline markers
OFFSET = wrap_ansi('\033[0m')
BLACK_FG = wrap_ansi('\033[30m')
RED_FG = wrap_ansi('\033[31m')
GREEN_FG = wrap_ansi('\033[32m')
YELLOW_FG = wrap_ansi('\033[33m')
BLUE_FG = wrap_ansi('\033[34m')
PURPLE_FG = wrap_ansi('\033[35m')
CYAN_FG = wrap_ansi('\033[36m')
WHITE_FG = wrap_ansi('\033[37m')
BLACK_BG = wrap_ansi('\033[40m')
RED_BG = wrap_ansi('\033[41m')
GREEN_BG = wrap_ansi('\033[42m')
YELLOW_BG = wrap_ansi('\033[43m')
BLUE_BG = wrap_ansi('\033[44m')
PURPLE_BG = wrap_ansi('\033[45m')
CYAN_BG = wrap_ansi('\033[46m')
WHITE_BG = wrap_ansi('\033[47m')

# some segments you may want to use
python_version = '  ' + ".".join(map(str, sys.version_info[:3]))
python_interpreter_path = ' 󰞷 ' + sys.executable
local_time = ' 󱑌 ' + time.strftime('%H:%M:%S', time.localtime(time.time()))
# the delimiter used at the end of a segment
delimiter = ''

# segments of the prompt
prompt_segments = [
    [BLUE_BG, WHITE_FG, python_version],
    [GREEN_BG, WHITE_FG, python_interpreter_path],
    [WHITE_BG, BLACK_FG, local_time]
]

# Build the prompt
sys.ps1 = ''
for i, (bg_color, fg_color, text) in enumerate(prompt_segments):
    # Add current segment
    sys.ps1 += bg_color + fg_color + text + ' '

    # Add transition to next segment or end
    if i < len(prompt_segments) - 1:
        # Get next segment's background color for transition
        next_bg = prompt_segments[i + 1][0]
        # Convert current background to foreground for the arrow
        current_bg_as_fg = wrap_ansi(re.sub(r'4(\d)', r'3\1', bg_color.strip('\001\002')))
        sys.ps1 += OFFSET + next_bg + current_bg_as_fg + delimiter
    else:
        # Last segment - transition to normal background
        current_bg_as_fg = wrap_ansi(re.sub(r'4(\d)', r'3\1', bg_color.strip('\001\002')))
        sys.ps1 += OFFSET + current_bg_as_fg + delimiter + OFFSET
