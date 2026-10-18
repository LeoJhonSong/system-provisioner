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
    "yazi",
    "fd",
    "fzf",
    "nmap",
    "curl",
    "wget",
    "git-lfs",
    "jq",
    "yq",  # jq 的 YAML/XML/TOML 包装, 依赖 jq
]

# 开发工具链.
# uv 一个包就带 uv 和 uvx 两个二进制, 不用 (也不能) 另外装 uvx: AUR 里那个
# uvx 是别的东西, 官方源没有
DEV_PACKAGES = [
    "base-devel",
    "gdb",
    "cmake",
    "nodejs",
    "npm",
    "jdk-openjdk",
    "uv",
    "just",
    "ruff",
    "github-cli",
]

# npm -g 的安装前缀. 默认是 /usr, 装全局包要 sudo, 且包会跟 pacman 管的
# /usr/lib/node_modules 混在一起. 改到 ~/.local 后 npm -g 落在
# ~/.local/bin, 免 sudo 且不碰系统目录
NPM_PREFIX = "${HOME}/.local"

# ~/.local/bin 入 PATH. 写 ~/.profile 而不是 .zshrc: 前者 login shell 与图形
# 会话都读, 且 common 层不该假定用户用 zsh (personal 的 default.zsh 已经自己
# export 过, 重复无害)
PROFILE_BLOCK = """export PATH="$HOME/.local/bin:$PATH"
"""

# 中文输入法与字体. fcitx5-im 是组名, pacman.packages 内部会用
# PacmanUnpackGroup 展开.
# xorg-xhost 提供 xhost, .xprofile 里的 `xhost +local:` 需要它
INPUT_PACKAGES = [
    "fcitx5-im",
    "fcitx5-material-color",
    "fcitx5-chinese-addons",
    "wqy-microhei",
    "xorg-xhost",
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

# 图形环境变量. 注意 .xprofile 只在 X11 会话下被 display manager source,
# Wayland 会话完全不读它, 本仓库 sddm 组把默认会话设成 plasmax11 所以够用.
#
# fcitx 三个变量是输入法接入各 GUI 工具包的开关. X11 下三个都要:
# XMODIFIERS 走 XIM 管旧的 X 程序, GTK_IM_MODULE / QT_IM_MODULE 让 GTK/Qt
# 直接加载 fcitx 的 im module. 上游 fcitx5 文档到现在仍把三个作为一套推荐.
# (Wayland 下反而不该全局设 GTK_IM_MODULE / QT_IM_MODULE, 会把原生 Wayland
#  客户端从 text-input 协议踢回 module 路径; 只有 XWayland 程序需要, 且该
#  按程序设. 将来真切到 Wayland 时这个 block 要重做.)
#
# xhost +local: 放开本机非当前用户 (含 root 与容器里同 UID 之外的进程) 连
# X server, 少数以别的身份起的 GUI 程序需要
XPROFILE_BLOCK = """# for fcitx input method
export GTK_IM_MODULE=fcitx
export QT_IM_MODULE=fcitx
export XMODIFIERS=@im=fcitx
# override QT scale
export QT_SCREEN_SCALE_FACTORS=1
# allow local non-current-user processes to reach the X server
xhost +local: >/dev/null 2>&1
"""


@deploy("包管理器")
def pacman_setup():
    """配置镜像源, 更新系统, 装 yay, 配置 yay, 给用户开 pacman 免密.

    免密规则是 yay 无人值守的必要条件: yay 拒绝以 root 运行, 以用户身份跑时
    内部自己调 `sudo pacman -U` 装构建产物. 那个 sudo 是 yay 的子进程, 既没有
    tty 也拿不到 pyinfra 的 askpass, 因此必须免密, 否则每个 AUR 包都会卡在
    密码提示上.

    安全代价: NOPASSWD 限定 `/usr/bin/pacman` 不构成有效隔离. pacman 能执行包
    自带的安装脚本, `-U` 能装任意本地构建的包, 因此这条规则等同于给该用户无密码
    root. 已知并接受.

    这条规则不会削减用户原有权限: sudo 按命令取最后一条匹配规则, 而它只匹配
    `/usr/bin/pacman`, 对其他命令不匹配, 因此 wheel 组的 `(ALL) ALL` 照旧生效.
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

    # 文件名前缀取 10, 保证在 sudoers.d 里靠前加载
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
    """编译工具链, node 与 java, 以及 pip/npm 的国内镜像."""
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

    # npm -g 的前缀改到 ~/.local, 之后所有 npm install -g 都不再需要 sudo.
    # npm 会展开 npmrc 值里的 ${HOME}, 所以这里存的是可移植的字面量
    files.line(
        name="配置 npm 全局前缀",
        path=f"{home}/.npmrc",
        line="^prefix=",
        replace=f"prefix={NPM_PREFIX}",
    )

    # ~/.local/bin 入 PATH, 否则 npm -g 装的东西调不到
    files.block(
        name="~/.local/bin 入 PATH",
        path=f"{home}/.profile",
        content=PROFILE_BLOCK,
        marker="# {mark} MANAGED BLOCK path",
    )

    # 不装 yarn: 它和 npm 是同类竞品而非上位替代, 手上的项目 lockfile 全是
    # package-lock.json, 没有 yarn.lock. 真遇到用 yarn 的仓库再说


@deploy("输入法")
def input_method():
    """fcitx5 全套, xhost, 图形环境变量, 拼音输入法 + 左 Shift 切换."""
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
