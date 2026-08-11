"""yay 配置算子.

只改无人值守时会卡住的两个键, 不整份覆盖 `config.json`:

- `removemake: "ask"` 会在装完 AUR 包后弹菜单问是否删构建依赖
- `provides: true` 会在包名有多个提供者时弹菜单让人选

其余键保持 yay 自己写的值. 整份 put 会有两个副作用: `version` 是 yay 自己维护
的状态 (每次 yay 升级后都报 changed), 手动改过的其它键也会被覆盖.
"""

from __future__ import annotations

from io import StringIO
import json

from pyinfra import host
from pyinfra.api import OperationError
from pyinfra.api import operation
from pyinfra.facts.files import FileContents
from pyinfra.facts.server import Home
from pyinfra.operations import files

# 无人值守必须定死的键
REQUIRED = {
    "removemake": "yes",
    "provides": False,
}


@operation()
def config():
    """把 yay 配置里几个会弹菜单的键改成无人值守可用的值."""
    home = host.get_fact(Home)
    config_path = f"{home}/.config/yay/config.json"

    lines = host.get_fact(FileContents, path=config_path)

    # 文件不存在: yay 还没跑过. 写一份只含必需键的配置, yay 首次运行时会
    # 自己补齐其余默认值
    if lines is None:
        current: dict = {}
    else:
        try:
            current = json.loads("\n".join(lines))
        except json.JSONDecodeError as error:
            raise OperationError(f"{config_path} 不是合法 JSON, 先手动修好再跑") from error

    if all(current.get(key) == value for key, value in REQUIRED.items()):
        host.noop("yay 配置已是无人值守可用的值")
        return

    merged = {**current, **REQUIRED}
    content = json.dumps(merged, indent="\t", ensure_ascii=False) + "\n"

    yield from files.put._inner(
        src=StringIO(content),
        dest=config_path,
        add_deploy_dir=False,
        mode="600",
    )
