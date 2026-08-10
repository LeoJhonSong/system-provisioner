"""company 层: 仅公司机要的配置.

目前为空, 但层机制要求此文件必须存在.
"""

from __future__ import annotations

from pyinfra.api import deploy


@deploy("占位")
def placeholder():
    """空函数, 防止 GROUPS 为空字典."""
    pass


GROUPS = {
    "placeholder": placeholder,
}
