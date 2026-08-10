"""common 层: 个人机与公司机都要的配置.

每个 `@deploy` 函数是一个可单独执行的组, 组名见 `GROUPS`.
"""

from __future__ import annotations

from io import StringIO

import aur
from pyinfra import host
from pyinfra.api import deploy
from pyinfra.facts.pacman import PacmanPackages
from pyinfra.facts.server import Home
from pyinfra.facts.server import User
from pyinfra.operations import files
from pyinfra.operations import pacman
from pyinfra.operations import server
from pyinfra.operations import systemd
import yay

# 命令行工具. tmux 配置见 oh-my-tmux (仓库内 vendored 两件套)
CLI_PACKAGES = [
    "tmux",
    "bat",
    "lsd",
    "yazi",
    "fd",
    "fzf",
    "nmap",
    "curl",
    "wget",
    "git-lfs",
]

# 开发工具链
DEV_PACKAGES = [
    "base-devel",
    "gdb",
    "cmake",
    "nodejs",
    "npm",
    "jdk-openjdk",
]

# 中文输入法与主题. fcitx5-im 是组名, pacman.packages 内部会用
# PacmanUnpackGroup 展开
INPUT_PACKAGES = [
    "fcitx5-im",
    "fcitx5-material-color",
    "fcitx5-chinese-addons",
    "kvantum",
    "wqy-microhei",
]

# 桌面应用, 官方源部分
APP_PACKAGES = [
    "gparted",
    "7zip",
]

# 桌面应用, AUR 部分
APP_AUR_PACKAGES = [
    "visual-studio-code-bin",
    "typora-free",
    "microsoft-edge-stable-bin",
    "snipaste",
    "ventoy-bin",
    "rar",
    # wps 四件套: 国内版本体 + 中文语言包 + 字体符号 + mime types
    "wps-office-cn",
    "wps-office-mui-zh-cn",
    "ttf-wps-fonts",
    "wps-office-mime-cn",
    # 即时通讯与会议
    "wechat-bin",
    "feishu-bin",
    "wemeet-bin",
]

# 图形环境变量. fcitx 三个是输入法接入各 GUI 工具包的开关,
# QT_STYLE_OVERRIDE 让 dolphin/kate 这类 Qt 程序走 kvantum 主题
XPROFILE_BLOCK = """# for fcitx input method
export GTK_IM_MODULE=fcitx
export QT_IM_MODULE=fcitx
export XMODIFIERS=@im=fcitx
# override QT scale
export QT_SCREEN_SCALE_FACTORS=1
# override QT style of applications like dolphin, kate
export QT_STYLE_OVERRIDE=kvantum
"""


@deploy("包管理器")
def pacman_setup():
    """装 yay, 配置 yay, 给用户开 pacman 免密.

    安全代价: NOPASSWD 限定 `/usr/bin/pacman` 不构成有效隔离. pacman 能执行包
    自带的安装脚本, `-U` 能装任意本地构建的包, 因此这条规则等同于给该用户无密码
    root. 采用它是因为 yay 拒绝以 root 运行且内部自己调 sudo, 无人值守时没有更
    好的选择 (paru 同样如此). 已知并接受.
    """
    pacman.packages(name="装 yay", packages=["yay"], _sudo=True)

    user = host.get_fact(User)
    files.put(
        name="给用户开 pacman 免密",
        src=StringIO(f"{user} ALL=(ALL) NOPASSWD: /usr/bin/pacman\n"),
        dest=f"/etc/sudoers.d/10-{user}-pacman",
        mode="440",
        add_deploy_dir=False,
        _sudo=True,
    )

    yay.config(name="配置 yay")


@deploy("命令行工具")
def cli():
    """命令行工具与 tmux 配置."""
    pacman.packages(name="装命令行工具", packages=CLI_PACKAGES, _sudo=True)

    # oh-my-tmux 全网无包, 两件套 vendored 在仓库里
    for filename in (".tmux.conf", ".tmux.conf.local"):
        files.put(
            name=f"放 {filename}",
            src=f"files/common/tmux/{filename}",
            dest=f"~/{filename}",
            mode="644",
        )

    files.directory(name="建 fd 配置目录", path="~/.config/fd", mode="755")
    files.put(
        name="放 fd ignore",
        src="files/common/fd/ignore",
        dest="~/.config/fd/ignore",
        mode="644",
    )


@deploy("开发工具链")
def dev():
    """编译工具链, node 与 java, 以及 pip/npm/yarn 的国内镜像."""
    pacman.packages(name="装开发工具链", packages=DEV_PACKAGES, _sudo=True)

    files.put(
        name="配置 pip 镜像",
        src=StringIO("[global]\nindex-url = https://mirrors.aliyun.com/pypi/simple/\n"),
        dest="~/.config/pip/pip.conf",
        mode="644",
        add_deploy_dir=False,
    )

    # 直接写配置文件而非 `npm config set`: 后者每次都报 changed
    files.file(name="touch ~/.npmrc", path="~/.npmrc", mode="644", touch=True)
    files.line(
        name="配置 npm 镜像",
        path="~/.npmrc",
        line="^registry=",
        replace="registry=https://registry.npmmirror.com",
    )

    # yarn 需全局装 (npm -g 需 sudo)
    server.shell(
        name="全局装 yarn",
        commands=["command -v yarn || npm install -g yarn"],
        _sudo=True,
    )

    files.file(name="touch ~/.yarnrc", path="~/.yarnrc", mode="644", touch=True)
    files.line(
        name="配置 yarn 镜像",
        path="~/.yarnrc",
        line='^registry "',
        replace='registry "https://registry.npmmirror.com"',
    )


@deploy("输入法")
def input_method():
    """fcitx5 全套与图形环境变量."""
    pacman.packages(name="装输入法", packages=INPUT_PACKAGES, _sudo=True)

    files.block(
        name="配置图形环境变量",
        path="~/.xprofile",
        content=XPROFILE_BLOCK,
        marker="# {mark} MANAGED BLOCK fcitx",
    )


@deploy("Docker")
def docker_setup():
    """Docker 与 compose, 服务自启, 用户入 docker 组."""
    pacman.packages(name="装 docker", packages=["docker", "docker-compose"], _sudo=True)

    systemd.service(name="启 docker 服务", service="docker", enabled=True, running=True, _sudo=True)

    user = host.get_fact(User)
    server.user(name="用户入 docker 组", user=user, groups=["docker"], _sudo=True)


@deploy("桌面应用")
def apps():
    """GUI 应用: VSCode, Typora, Edge, Snipaste, WPS, 即时通讯."""
    pacman.packages(name="装桌面应用 (官方源)", packages=APP_PACKAGES, _sudo=True)
    aur.packages(APP_AUR_PACKAGES)


# 组名注册. deploy.py 按 only/skip 过滤
GROUPS = {
    "pacman": pacman_setup,
    "cli": cli,
    "dev": dev,
    "input": input_method,
    "docker": docker_setup,
    "apps": apps,
}
