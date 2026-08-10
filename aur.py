"""AUR 包管理算子.

yay 拒绝以 root 身份运行, 内部自己调 sudo. 因此所有 yay 命令以用户自己的身份
执行 (`_sudo=False`), 免密提权靠 `/etc/sudoers.d/` 里限定 `/usr/bin/pacman` 的
规则 (见 `layers/common.py`). 构建缓存因此落在用户自己的 `~/.cache/yay`, 可命中.

幂等判断直接复用 `PacmanPackages` fact: `pacman -Q` 的输出包含 AUR 包, 无需
单独查询 AUR.
"""

from __future__ import annotations

from pyinfra import host
from pyinfra import logger
from pyinfra.api import QuoteString
from pyinfra.api import StringCommand
from pyinfra.api import operation
from pyinfra.facts.pacman import PacmanPackages


@operation()
def package(pkg: str):
    """装单个 AUR 包.

    参数名不用 `name`: 那是 pyinfra 所有算子的保留全局参数 (算子显示名).

    + pkg: 包名
    """
    if pkg in host.get_fact(PacmanPackages):
        host.noop(f"AUR 包 {pkg} 已安装")
        return

    yield StringCommand("yay", "--noconfirm", "-S", QuoteString(pkg))


def packages(names: list[str]) -> None:
    """装一批 AUR 包, 逐包容错.

    不是算子而是普通函数: AUR 构建失败是常态 (源站挂掉, 上游改了 tarball,
    需要手工下载的商业软件), 单个包失败不该中断整个部署. 每个缺失的包声明为
    一个独立算子并带 `_ignore_errors`, 失败只记 warning.

    差集在这里先算一遍, 已装的包不声明算子, 稳定状态下零操作.

    代理环境变量不在这里传: deploy.py 在层级注入 `_env`, 按全局参数优先级
    (直接调用 > deploy kwargs > host data > config) 自动传播到内层算子.

    + names: 包名列表
    """
    installed = host.get_fact(PacmanPackages)
    missing = [name for name in names if name not in installed]

    if not missing:
        return

    logger.info(f"待装 AUR 包 {len(missing)} 个: {' '.join(missing)}")

    for pkg in missing:
        package(
            name=f"装 AUR 包 {pkg}",
            pkg=pkg,
            _sudo=False,
            _ignore_errors=True,
        )
