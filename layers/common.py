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
    "plasma-x11-session",  # KDE X11 session, 很多软件需要 X11
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
    """配置镜像源, 更新系统, 装 yay, 配置 yay.

    不给用户加 NOPASSWD sudoers 规则: Manjaro 默认用户在 wheel 组已有
    `(ALL) ALL`, 配合部署时传入的 sudo 密码, yay 本就能跑. 而 sudoers.d 里
    只授权单条命令的规则, 因对同一用户以最后匹配为准, 有覆盖 wheel 那条
    `ALL` 的风险, 反而降权.
    """
    # 配置 Manjaro 中国镜像源 (按速度排序, 非交互式)
    server.shell(
        name="配置中国镜像源",
        commands=["pacman-mirrors -c China -m rank"],
        _sudo=True,
    )

    # 更新软件包数据库
    pacman.update(name="更新软件包数据库", _sudo=True)

    # 升级所有已安装的包 (pacman -Su)
    pacman.upgrade(name="升级所有包", _sudo=True)

    pacman.packages(name="装 yay", packages=["yay"], _sudo=True)

    yay.config(name="配置 yay")


@deploy("命令行工具")
def cli():
    """命令行工具与 tmux 配置."""
    pacman.packages(name="装命令行工具", packages=CLI_PACKAGES, _sudo=True)

    home = host.get_fact(Home)

    # oh-my-tmux 全网无包, 两件套 vendored 在仓库里
    for filename in (".tmux.conf", ".tmux.conf.local"):
        files.put(
            name=f"放 {filename}",
            src=f"files/common/tmux/{filename}",
            dest=f"{home}/{filename}",
            mode="644",
        )

    files.directory(name="建 fd 配置目录", path=f"{home}/.config/fd", mode="755")
    files.put(
        name="放 fd ignore",
        src="files/common/fd/ignore",
        dest=f"{home}/.config/fd/ignore",
        mode="644",
    )


@deploy("开发工具链")
def dev():
    """编译工具链, node 与 java, 以及 pip/npm/yarn 的国内镜像."""
    pacman.packages(name="装开发工具链", packages=DEV_PACKAGES, _sudo=True)

    home = host.get_fact(Home)

    files.put(
        name="配置 pip 镜像",
        src=StringIO("[global]\nindex-url = https://mirrors.aliyun.com/pypi/simple/\n"),
        dest=f"{home}/.config/pip/pip.conf",
        mode="644",
        add_deploy_dir=False,
    )

    # 直接写配置文件而非 `npm config set`: 后者每次都报 changed
    files.file(name="touch .npmrc", path=f"{home}/.npmrc", mode="644", touch=True)
    files.line(
        name="配置 npm 镜像",
        path=f"{home}/.npmrc",
        line="^registry=",
        replace="registry=https://registry.npmmirror.com",
    )

    # yarn 需全局装 (npm -g 需 sudo)
    server.shell(
        name="全局装 yarn",
        commands=["command -v yarn || npm install -g yarn"],
        _sudo=True,
    )

    files.file(name="touch .yarnrc", path=f"{home}/.yarnrc", mode="644", touch=True)
    files.line(
        name="配置 yarn 镜像",
        path=f"{home}/.yarnrc",
        line='^registry "',
        replace='registry "https://registry.npmmirror.com"',
    )


@deploy("输入法")
def input_method():
    """fcitx5 全套与图形环境变量, 拼音输入法 + 左 Shift 切换."""
    pacman.packages(name="装输入法", packages=INPUT_PACKAGES, _sudo=True)

    home = host.get_fact(Home)

    files.block(
        name="配置图形环境变量",
        path=f"{home}/.xprofile",
        content=XPROFILE_BLOCK,
        marker="# {mark} MANAGED BLOCK fcitx",
    )

    # fcitx5 用户配置: profile (输入法列表) + config (快捷键)
    files.directory(name="建 fcitx5 配置目录", path=f"{home}/.config/fcitx5", mode="700")

    for filename in ("profile", "config"):
        files.put(
            name=f"放 fcitx5/{filename}",
            src=f"files/common/fcitx5/{filename}",
            dest=f"{home}/.config/fcitx5/{filename}",
            mode="600",
        )


@deploy("Docker")
def docker_setup():
    """Docker 与 compose, 服务自启, 用户入 docker 组."""
    pacman.packages(name="装 docker", packages=["docker", "docker-compose"], _sudo=True)

    systemd.service(name="启 docker 服务", service="docker", enabled=True, running=True, _sudo=True)

    # append=True 是必须的: 不传时 groups 是声明式的, 会把用户的附加组设成
    # 恰好等于列表内容, 把 wheel 等原有组全部删掉 (连带丢失 sudo 权限)
    user = host.get_fact(User)
    server.user(
        name="用户入 docker 组",
        user=user,
        groups=["docker"],
        append=True,
        _sudo=True,
    )


@deploy("桌面应用")
def apps():
    """GUI 应用: VSCode, Typora, Edge, Snipaste, WPS, 即时通讯."""
    pacman.packages(name="装桌面应用 (官方源)", packages=APP_PACKAGES, _sudo=True)
    aur.packages(APP_AUR_PACKAGES)


@deploy("SDDM X11")
def sddm_x11():
    """配置 SDDM 默认用 X11 session (plasmax11).

    Manjaro KDE 默认 Wayland, 但很多软件需要 X11. 这里改
    `/etc/sddm.conf.d/kde_settings.conf` 的 `[Autologin] Session=`.
    """
    files.line(
        name="SDDM 默认 X11 session",
        path="/etc/sddm.conf.d/kde_settings.conf",
        line="^Session=",
        replace="Session=plasmax11",
        _sudo=True,
    )


@deploy("Claude 工具")
def claude_tools():
    """claude-code, cc-switch-cli, claude-history."""
    # claude-code AUR 无官方包, 用官方脚本
    server.shell(
        name="装 claude-code",
        commands=["command -v claude || curl -fsSL https://claude.ai/install.sh | bash"],
    )

    # cc-switch-cli 与 claude-history 从 AUR 装
    aur.packages(["cc-switch-cli-git", "claude-history"])


# 组名注册. deploy.py 按 only/skip 过滤
GROUPS = {
    "pacman": pacman_setup,
    "cli": cli,
    "dev": dev,
    "input": input_method,
    "docker": docker_setup,
    "apps": apps,
    "sddm": sddm_x11,
    "claude": claude_tools,
}
