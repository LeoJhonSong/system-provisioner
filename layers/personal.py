"""personal 层: 仅个人机要的配置.

每个 `@deploy` 函数是一个可单独执行的组, 组名见 `GROUPS`.
"""

from __future__ import annotations

from io import StringIO
from pathlib import Path

import aur
from pyinfra import host
from pyinfra.api import deploy
from pyinfra.facts.files import File
from pyinfra.facts.server import Home
from pyinfra.facts.server import Hostname
from pyinfra.operations import files
from pyinfra.operations import git
from pyinfra.operations import pacman
from pyinfra.operations import server
from pyinfra.operations import systemd

# 仓库根目录绝对路径, 用于构造 ~/.config/zsh 软链的 target
REPO_ROOT = Path.cwd().resolve()

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
    "davinci-resolve-studio",
    "audiorelay",
    "deadbeef",
    "deadbeef-plugin-customizabletb-gtk3-git",
    "deadbeef-plugin-waveform-gtk3-git",
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
]


def _zshrc_skeleton_template(home: str, proxy: str) -> str:
    """生成 .zshrc 骨架模板.

    source manjaro 打底配置, 再 source 仓库内同步的定制. 可选注入 PROXY 变量.
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
    ]
    if proxy:
        lines.extend([f'export PROXY="{proxy}"', ""])
    lines.extend(
        [
            "# source 仓库内同步的定制配置",
            f"if [[ -f {home}/.config/zsh/default.zsh ]]; then",
            f"  source {home}/.config/zsh/default.zsh",
            "fi",
            "",
        ]
    )
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

    # ~/.config/zsh 软链到仓库内 files/personal/zsh, 编辑即生效且改动回流
    files.link(
        name="软链 ~/.config/zsh",
        path=f"{home}/.config/zsh",
        target=str(REPO_ROOT / "files/personal/zsh"),
    )

    # .zshrc 骨架: 判存, 不存在才 put, 已存在完全不动 (本机私有改动)
    if not host.get_fact(File, path=f"{home}/.zshrc"):
        proxy = host.data.get("proxy", "")
        files.template(
            name="写 .zshrc 骨架",
            src=StringIO(_zshrc_skeleton_template(home, proxy)),
            dest=f"{home}/.zshrc",
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

    files.link(
        name="软链 aria2.conf",
        path=f"{home}/.config/aria2/aria2.conf",
        target=str(REPO_ROOT / "files/personal/aria2.conf"),
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
    files.put(
        name="OneDriveGUI 自启",
        src="/usr/share/applications/OneDriveGUI.desktop",
        dest=f"{home}/.config/autostart/OneDriveGUI.desktop",
        mode="644",
        _sudo_user=home.split("/")[-1],
    )


@deploy("杂项工具")
def extras():
    """录屏, 串口, samba, filezilla, github-desktop 等."""
    pacman.packages(name="装杂项工具 (官方源)", packages=EXTRAS_PACKAGES, _sudo=True)
    aur.packages(EXTRAS_AUR_PACKAGES)


@deploy("Windows 卷挂载")
def disk_mount():
    """挂载 Windows 卷 (仅个人机有)."""
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
        replace="LABEL=Windows /run/media/Windows ntfs defaults 0 0",
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
    "disk": disk_mount,
}
