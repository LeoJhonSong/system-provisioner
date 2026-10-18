"""system-provisioner 部署入口.

用法:
    个人机: pyinfra @local deploy.py --data profile=personal [--data proxy=http://...]
    公司机: pyinfra <ip> deploy.py --data profile=company --user <u> --ssh-password-prompt --sudo --use-sudo-password

选择性执行:
    只跑几组: --data only=zsh,cli
    跳过几组: --data skip=latex,media
"""

from __future__ import annotations

from layers import common
from layers import company
from layers import personal
from pyinfra import host
from pyinfra import logger
from pyinfra.api import DeployError

# profile → 层模块映射
LAYERS = {
    "personal": [common, personal],
    "company": [common, company],
}

# 优先执行的组, 按此顺序最先跑, 其余组随后按各层 GROUPS 的定义顺序跑.
# 目标是部署没跑完就能开始干活: 镜像源与系统升级 → 构建工具 (AUR 依赖
# base-devel) → 浏览器 (先登录账号, 自己搜索下载) → 输入法 → claude
# → 即时通讯 → 办公. 当前 profile 没有的组跳过
PRIORITY = ["pacman", "dev", "browser", "input", "claude", "im", "wps", "office"]


def main():
    """主入口: 读 profile, 过滤组, 依次调用."""
    profile = host.data.get("profile")
    if not profile:
        raise DeployError("缺 --data profile=personal|company. 不设默认值: 防忘传参数把 texlive 全家桶装到公司机")

    if profile not in LAYERS:
        raise DeployError(f"未知 profile: {profile}. 可选: {list(LAYERS.keys())}")

    layers = LAYERS[profile]

    # 收集选中的层的所有组名
    all_groups = {}
    for layer in layers:
        all_groups.update(layer.GROUPS)
    first = {g: all_groups[g] for g in PRIORITY if g in all_groups}
    all_groups = first | all_groups

    # 过滤: only 与 skip 互斥, 都不传 = 全量
    only = host.data.get("only", "")
    skip = host.data.get("skip", "")

    if only and skip:
        raise DeployError("only 与 skip 不能同时传")

    if only:
        requested = [g.strip() for g in only.split(",")]
        unknown = set(requested) - set(all_groups.keys())
        if unknown:
            raise DeployError(f"未知组名: {sorted(unknown)}. 可选 ({profile}): {sorted(all_groups.keys())}")
        selected = {g: all_groups[g] for g in requested}
    elif skip:
        skipped = [g.strip() for g in skip.split(",")]
        unknown = set(skipped) - set(all_groups.keys())
        if unknown:
            raise DeployError(f"未知组名: {sorted(unknown)}. 可选 ({profile}): {sorted(all_groups.keys())}")
        selected = {g: f for g, f in all_groups.items() if g not in skipped}
    else:
        selected = all_groups

    if not selected:
        logger.warning(f"过滤后无组可执行 (profile={profile}, only={only}, skip={skip})")
        return

    logger.info(f"profile={profile}, 将执行 {len(selected)} 组: {list(selected.keys())}")

    # 注入代理环境变量到 deploy 上下文
    proxy = host.data.get("proxy", "")
    proxy_env = {}
    if proxy:
        proxy_env = {"http_proxy": proxy, "https_proxy": proxy}
        logger.info(f"代理: {proxy}")

    # 依次执行选中的组
    #
    # _sudo=False 是这里的默认值, 不是命令行的 --sudo. 提权范围由代码掌控:
    # 层里标了 _sudo=True 的算子 (装包, 改 /etc) 会覆盖这个默认值, 因为全局
    # 参数优先级是 直接调用 > deploy kwargs > host data > config.
    #
    # 反过来 (命令行给 --sudo, 代码里逐个标 _sudo=False) 需要在 23 处用户级
    # 操作上标注, 漏一处就把用户配置文件写成 root 所有.
    for group_name, group_func in selected.items():
        group_func(_env=proxy_env, _sudo=False)


# 直接调用, pyinfra 通过 import 加载 deploy 文件
main()
