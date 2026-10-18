"""personal 层: 仅个人机要的配置.

每个 `@deploy` 函数是一个可单独执行的组, 组名见 `GROUPS`.
"""

from __future__ import annotations

from io import StringIO

import aur
from pyinfra import host
from pyinfra.api import deploy
from pyinfra.facts.files import File
from pyinfra.facts.files import FindInFile
from pyinfra.facts.server import Home
from pyinfra.facts.server import Hostname
from pyinfra.operations import files
from pyinfra.operations import git
from pyinfra.operations import pacman
from pyinfra.operations import server
from pyinfra.operations import systemd

# 部署仓库在目标机上的位置 (相对家目录). 本机就是控制端这份仓库本身;
# 远程个人机由 _clone_repo 拉下来. 软链与 source 都指向目标机上的这份
REPO_DIR = "projects/system-provisioner"
REPO_URL = "https://github.com/LeoJhonSong/system-provisioner"

# .zshrc 引用的仓库内 zsh 配置, 也用作判断 .zshrc 是否为本仓库所写
ZSH_DEFAULT = f"{REPO_DIR}/files/personal/zsh/default.zsh"


def _clone_repo(home: str) -> str:
    """确保部署仓库在目标机 ~/projects 下, 返回其绝对路径.

    只 clone 不 pull, 与 Shell-Scripts 一致. 用到仓库文件的组各自调用,
    单独跑某组时也不会出现悬空软链; 重复声明只是 no-op.
    """
    git.repo(name="clone system-provisioner", src=REPO_URL, dest=f"{home}/{REPO_DIR}", pull=False)
    return f"{home}/{REPO_DIR}"


# graphics 组
GRAPHICS_PACKAGES = [
    "drawio-desktop",
    "gimp",
    "inkscape",
    "blender",
    "libjxl",
    "oxipng",
    "ghostscript",
]

# media 组. vlc / handbrake 已提到 common 层
MEDIA_PACKAGES = ["kdenlive", "wine", "winetricks"]
MEDIA_AUR_PACKAGES = [
    # davinci-resolve-studio: 故意不装. 这个 PKGBUILD 不下载安装包, 要自己去
    # 官网 (需登录) 下 DaVinci_Resolve_Studio_*_Linux.zip 手动放进 ~/.cache/yay
    # 对应目录后再 yay -S. 留个记录, 别忘了有这东西.
    "audiorelay",
]

# latex 组
LATEX_PACKAGES = [
    "texlive-basic",
    "texlive-lang",
    "texlive-xetex",
    "texlive-luatex",
    "texlive-latexextra",
    "texlive-plaingeneric",
    "texlive-bibtexextra",
    "texlive-mathscience",
    "texlive-binextra",
    "perl-yaml-tiny",
    "perl-file-homedir",
    "biber",
    "python-pygments",
]

# office 组
OFFICE_AUR_PACKAGES = [
    "linuxqq",
    "zotero-beta-bin",
    "zoom",
    "onedrive-abraunegg",
    "onedrivegui-git",
]

# extras 组
EXTRAS_PACKAGES = [
    "kooha",
    "screenkey",
    "aria2",
    "manjaro-settings-samba",
    "filezilla",
]
EXTRAS_AUR_PACKAGES = [
    "github-desktop-bin",
    "python-comtool",
    "ccze",
    "appimagelauncher",
]

# fonts 组. 阿里巴巴普惠体, Operator Mono 无包, 手动放 ~/.local/share/fonts
FONT_PACKAGES = ["ttf-firacode-nerd"]

# localbin 组: 放进 ~/.local/bin 的自写小脚本 (files/personal/bin/)
LOCAL_BIN_SCRIPTS = [
    "dde-file-manager",  # 微信 "打开所在文件夹" 调的是 dde-file-manager, 转给 dolphin
    "snipaste-launcher",
]

# remote 组: 远程桌面, 代理, VPN, 内网穿透
REMOTE_PACKAGES = [
    "networkmanager-openconnect",
    "networkmanager-vpnc",
    "networkmanager-openvpn",
    "networkmanager-l2tp",
]
# frpc 只装不配: 配置在 /etc/frp/frpc.toml, 需手写. 2026-10-06 本机经 frp
# 映射到公网的 22 端口被 SSH 爆破入侵, 不要再映射 sshd, 远程登录走 tailscale
REMOTE_AUR_PACKAGES = [
    "anydesk-bin",
    "rustdesk-bin",
    "todesk-bin",
    "clash-verge-rev-bin",
    "openvpn3",
    "frpc-bin",
]

# robotics 组
ROBOTICS_AUR_PACKAGES = [
    "foxglove-bin",
    "python-rosbags",
]


def _zshrc_skeleton_template(home: str, proxy: str) -> str:
    """生成 .zshrc 骨架模板.

    顺序: manjaro 打底配置 → 仓库内定制 (覆盖 manjaro 默认值) → 本机私有部分
    (可选 PROXY, 及日后手加的内容, 覆盖仓库定制).
    """
    lines = [
        "# source manjaro-zsh-config",
        "if [[ -e /usr/share/zsh/manjaro-zsh-config ]]; then",
        "  source /usr/share/zsh/manjaro-zsh-config",
        "fi",
        "if [[ -e /usr/share/zsh/manjaro-zsh-prompt ]]; then",
        "  source /usr/share/zsh/manjaro-zsh-prompt",
        "fi",
        "",
        "# source 部署仓库内的定制配置",
        f"if [[ -f {home}/{ZSH_DEFAULT} ]]; then",
        f"  source {home}/{ZSH_DEFAULT}",
        "fi",
        "",
        "# ---- 以下为本机私有配置 ----",
        "",
    ]
    if proxy:
        lines.extend([f'export PROXY="{proxy}"', ""])
    return "\n".join(lines)


@deploy("zsh")
def zsh_setup():
    """zsh 配置: omz + 插件 + 自定义配置."""
    home = host.get_fact(Home)

    # pkgfile 替代 antigen 的 command-not-found bundle
    pacman.packages(name="装 pkgfile", packages=["pkgfile"], _sudo=True)
    server.shell(
        name="更新 pkgfile 数据库",
        commands=["pkgfile --update || true"],
        _sudo=True,
    )
    systemd.service(
        name="启 pkgfile 定时更新",
        service="pkgfile-update.timer",
        enabled=True,
        _sudo=True,
    )

    git.repo(
        name="clone oh-my-zsh",
        src="https://github.com/ohmyzsh/ohmyzsh",
        dest=f"{home}/.oh-my-zsh",
        pull=False,
    )

    git.repo(
        name="clone Shell-Scripts",
        src="https://github.com/LeoJhonSong/Shell-Scripts",
        dest=f"{home}/projects/Shell-Scripts",
        pull=False,
    )

    _clone_repo(home)

    # .zshrc: 不是本仓库写的 (没引用仓库内 default.zsh, 如 Manjaro 自带的)
    # 就整体备份后重写骨架; 已是本仓库写的则不动 (保留本机私有改动)
    zshrc = f"{home}/.zshrc"
    if host.get_fact(File, path=zshrc) and host.get_fact(FindInFile, path=zshrc, pattern=ZSH_DEFAULT):
        return
    server.shell(
        name="备份原 .zshrc",
        commands=[f'[ -f {zshrc} ] && cp -a {zshrc} {zshrc}.bak.$(date +%Y%m%d%H%M%S) || true'],
    )
    files.template(
        name="写 .zshrc 骨架",
        src=StringIO(_zshrc_skeleton_template(home, host.data.get("proxy", ""))),
        dest=zshrc,
        mode="644",
    )


@deploy("git")
def git_setup():
    """git 配置: user.name 用 hostname, email 与 credential.helper."""
    hostname = host.get_fact(Hostname)
    git.config(name="配 git user.name", key="user.name", value=hostname)
    git.config(name="配 git user.email", key="user.email", value="LeoJhon.Song@outlook.com")
    git.config(name="配 git credential.helper", key="credential.helper", value="store")


@deploy("python")
def python_setup():
    """pyenv 与 .pythonrc.py."""
    home = host.get_fact(Home)

    pacman.packages(name="装 pyenv", packages=["pyenv"], _sudo=True)
    files.put(
        name="放 .pythonrc.py",
        src="files/personal/.pythonrc.py",
        dest=f"{home}/.pythonrc.py",
        mode="644",
    )


@deploy("wakatime")
def wakatime_setup():
    """wakatime-cli 与 .wakatime.cfg."""
    home = host.get_fact(Home)

    server.shell(
        name="装 wakatime-cli",
        commands=[
            'python3 -c "$(wget -q -O - https://raw.githubusercontent.com/wakatime/vim-wakatime/master/scripts/install_cli.py)" || true'
        ],
    )
    files.put(
        name="放 .wakatime.cfg",
        src="files/personal/.wakatime.cfg",
        dest=f"{home}/.wakatime.cfg",
        mode="600",
    )


@deploy("clang")
def clang_setup():
    """clang 工具链与 .clang-format."""
    home = host.get_fact(Home)

    pacman.packages(name="装 clang/bear", packages=["clang", "bear"], _sudo=True)
    files.put(
        name="放 .clang-format",
        src="files/personal/.clang-format",
        dest=f"{home}/.clang-format",
        mode="644",
    )


@deploy("aria2")
def aria2_setup():
    """aria2 配置与自启."""
    home = host.get_fact(Home)

    repo = _clone_repo(home)
    files.link(
        name="软链 aria2.conf",
        path=f"{home}/.config/aria2/aria2.conf",
        target=f"{repo}/files/personal/aria2.conf",
    )


@deploy("Kvantum 主题")
def kvantum_setup():
    """装 kvantum 并把 Plasma 的控件样式设成 kvantum.

    以前是在 .xprofile 里写 QT_STYLE_OVERRIDE=kvantum. 那个变量本身没被废弃,
    但按 Kvantum 上游文档它是给"没有 Qt 样式配置工具的桌面"用的兜底手段; 在
    KDE 上正规做法是 System Settings > Application Style > Widget Style 选
    Kvantum, 落到 kdeglobals 的 [KDE] widgetStyle. 环境变量优先级更高, 会盖掉
    Plasma 自己的设置, 反而让系统设置里改样式看起来"没反应", 所以这里改成写
    kdeglobals.

    kvantum 是 Qt6 版, Qt5 程序 (比如一些没迁完的老 KDE 应用) 另需 kvantum-qt5.
    具体主题用 Kvantum Manager (kvantummanager) 挑, 那是 per-user 的 GUI 状态,
    不在这里管.
    """
    pacman.packages(
        name="装 kvantum",
        packages=["kvantum", "kvantum-qt5"],
        _sudo=True,
    )

    # 用 kwriteconfig6 而不是 files.line: widgetStyle 要落在 kdeglobals 的
    # [KDE] 段里, 而这个 key 默认不在 ~/.config/kdeglobals (值由 look-and-feel
    # 包提供), files.line 匹配不到就会 append 到文件末尾, 掉进最后一个 INI
    # 段, 不生效. kwriteconfig6 认段, 没有会自己建.
    # 已登录的 Plasma 会话不会立刻生效, 重新登录后生效.
    server.shell(
        name="Plasma 控件样式设为 kvantum",
        commands=["kwriteconfig6 --file kdeglobals --group KDE --key widgetStyle kvantum"],
    )


@deploy("图形软件")
def graphics():
    """绘图与图形处理软件."""
    pacman.packages(name="装图形软件", packages=GRAPHICS_PACKAGES, _sudo=True)


@deploy("媒体软件")
def media():
    """视频编辑与音频播放器."""
    pacman.packages(name="装媒体软件 (官方源)", packages=MEDIA_PACKAGES, _sudo=True)
    aur.packages(MEDIA_AUR_PACKAGES)


@deploy("LaTeX")
def latex_setup():
    """texlive 全套与依赖."""
    pacman.packages(name="装 texlive", packages=LATEX_PACKAGES, _sudo=True)


@deploy("办公软件")
def office():
    """zotero, onedrive, linuxqq, zoom."""
    home = host.get_fact(Home)

    aur.packages(OFFICE_AUR_PACKAGES)

    # OneDriveGUI 自启
    # 不用 files.put: 它的 src 读的是控制端的文件, 而 .desktop 由上面的
    # AUR 包装到目标机, 只能在目标机上拷
    server.shell(
        name="OneDriveGUI 自启",
        commands=[
            f"install -Dm644 /usr/share/applications/OneDriveGUI.desktop {home}/.config/autostart/OneDriveGUI.desktop"
        ],
    )


@deploy("杂项工具")
def extras():
    """录屏, 串口, samba, filezilla, github-desktop 等."""
    pacman.packages(name="装杂项工具 (官方源)", packages=EXTRAS_PACKAGES, _sudo=True)
    aur.packages(EXTRAS_AUR_PACKAGES)


@deploy("字体")
def fonts():
    """FiraCode Nerd Font."""
    pacman.packages(name="装字体", packages=FONT_PACKAGES, _sudo=True)


@deploy("~/.local/bin")
def local_bin():
    """自写小脚本与 dev-browser.

    dev-browser 走 npm -g, 依赖 common 层 dev 组把 npm 前缀改到 ~/.local.
    判存用绝对路径, 理由同 common 层的 ccstatusline.
    """
    home = host.get_fact(Home)
    files.directory(name="建 ~/.local/bin", path=f"{home}/.local/bin", mode="755")
    for filename in LOCAL_BIN_SCRIPTS:
        files.put(
            name=f"放 {filename}",
            src=f"files/personal/bin/{filename}",
            dest=f"{home}/.local/bin/{filename}",
            mode="755",
        )
    server.shell(
        name="全局装 dev-browser",
        commands=[f'test -x "{home}/.local/bin/dev-browser" || npm install -g dev-browser'],
    )


@deploy("远程与网络")
def remote():
    """远程桌面 (anydesk, rustdesk, todesk), clash, VPN 插件, frpc."""
    pacman.packages(name="装 VPN 插件 (官方源)", packages=REMOTE_PACKAGES, _sudo=True)
    aur.packages(REMOTE_AUR_PACKAGES)


@deploy("机器人工具")
def robotics():
    """foxglove 与 rosbag 读写库."""
    aur.packages(ROBOTICS_AUR_PACKAGES)


@deploy("Windows 卷挂载")
def disk_mount():
    """挂载 Windows 卷 (仅个人机有)."""
    # /run 是 tmpfs, 挂载点每次开机都要重建; 开机时由 fstab 挂载 (systemd 会自建),
    # 这里只管本次部署
    files.directory(name="建挂载点", path="/run/media/Windows", _sudo=True)
    server.mount(
        name="挂 Windows 卷",
        path="/run/media/Windows",
        device="LABEL=Windows",
        fs_type="ntfs",
        mounted=True,
        _sudo=True,
    )

    # server.mount 不写 fstab, 需另行补
    files.line(
        name="写 /etc/fstab",
        path="/etc/fstab",
        line="^LABEL=Windows",
        # nofail: 盘不在或挂不上 (如 Windows 休眠) 时不让开机卡进紧急模式
        replace="LABEL=Windows /run/media/Windows ntfs defaults,nofail 0 0",
        _sudo=True,
    )


# 组名注册
GROUPS = {
    "zsh": zsh_setup,
    "git": git_setup,
    "python": python_setup,
    "wakatime": wakatime_setup,
    "clang": clang_setup,
    "aria2": aria2_setup,
    "kvantum": kvantum_setup,
    "graphics": graphics,
    "media": media,
    "latex": latex_setup,
    "office": office,
    "extras": extras,
    "fonts": fonts,
    "localbin": local_bin,
    "remote": remote,
    "robotics": robotics,
    "disk": disk_mount,
}
