"""common 层: 个人机与公司机都要的配置.

每个 `@deploy` 函数是一个可单独执行的组, 组名见 `GROUPS`.
"""

from __future__ import annotations

from io import StringIO
import json

import aur
from pyinfra import host
from pyinfra import logger
from pyinfra.api import deploy
from pyinfra.facts.server import Home
from pyinfra.facts.server import Mounts
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
    "xclip",
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
    "vlc",
    "handbrake",
]

# 桌面应用, AUR 部分 (浏览器单独成组, 见下)
APP_AUR_PACKAGES = [
    "visual-studio-code-bin",
    "typora-free",
    "snipaste",
    "simplescreenrecorder",
    "ventoy-bin",
    "rar",
]

# browser 组. 单独成组以便最先装: 部署没跑完就能先登录各种账号, 自己搜索下载
BROWSER_AUR_PACKAGES = ["microsoft-edge-stable-bin"]

# 即时通讯与会议 (apps 组)
IM_AUR_PACKAGES = ["wechat-bin", "feishu-bin", "wemeet-bin"]

# WPS (apps 组): 国内版本体 + 中文语言包 + 字体符号 + mime types
WPS_AUR_PACKAGES = [
    "wps-office-cn",
    "wps-office-mui-zh-cn",
    "ttf-wps-fonts",
    "wps-office-mime-cn",
]

WPS_LANG_SCRIPT = r"""f="$HOME/.config/Kingsoft/Office.conf"
mkdir -p "$(dirname "$f")" && touch "$f"
awk '/^\[/{s=($0=="[General]")} s && $0=="languages=zh_CN"{ok=1} END{exit !ok}' "$f" && exit 0
awk '
/^\[/ {s = ($0 == "[General]")}
s && /^languages=/ {next}
{print}
$0 == "[General]" && !done {print "languages=zh_CN"; done = 1}
END {if (!done) printf "\n[General]\nlanguages=zh_CN\n"}
' "$f" > "$f.tmp" && mv "$f.tmp" "$f"
"""

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


@deploy("浏览器")
def browser():
    """Edge."""
    aur.packages(BROWSER_AUR_PACKAGES)


@deploy("桌面应用")
def apps():
    """即时通讯 (微信, 飞书, 腾讯会议), WPS, VSCode, Typora, Snipaste, 录屏, 播放器.

    即时通讯与 WPS 排在前面: 部署没跑完时它们最先能用上.
    """
    aur.packages(IM_AUR_PACKAGES)
    aur.packages(WPS_AUR_PACKAGES)

    # WPS 界面语言默认跟系统 locale 走 (en_US 下就是英文), 中文要在
    # ~/.config/Kingsoft/Office.conf 的 [General] 段写 languages=zh_CN.
    # 这个文件 WPS 运行时会写入大量状态, 不能整体 put, 只改这一行:
    # 删掉 [General] 里已有的 languages= 后在段首插入, 没有该段就追加
    server.shell(
        name="WPS 界面语言设为中文",
        commands=[WPS_LANG_SCRIPT],
    )

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
    home = host.get_fact(Home)

    # claude-code AUR 无官方包, 用官方脚本
    server.shell(
        name="装 claude-code",
        commands=["command -v claude || curl -fsSL https://claude.ai/install.sh | bash"],
    )

    # cc-switch-cli 用官方脚本装预编译二进制 (装到 ~/.local/bin/cc-switch).
    # 守卫必须留: 脚本检测到已装且无 tty 时直接 exit 1. 判存用绝对路径而非
    # command -v, 因为 pyinfra 的非登录 shell 里 PATH 未必含 ~/.local/bin
    server.shell(
        name="装 cc-switch-cli",
        commands=[
            (
                'test -x "$HOME/.local/bin/cc-switch" || '
                "curl -fsSL https://github.com/SaladDay/cc-switch-cli/releases/latest/download/install.sh | bash"
            )
        ],
    )

    aur.packages(["claude-history"])

    # 完成/通知提示音 hooks 用 paplay (libpulse) 播 freedesktop 音效主题里的 .oga
    pacman.packages(
        name="装提示音依赖",
        packages=["libpulse", "sound-theme-freedesktop"],
        _sudo=True,
    )

    cc_switch = f"{home}/.local/bin/cc-switch"

    # 状态栏由两个脚本拼成: statusline-command.sh 出 git 信息,
    # statusline-wrapper.sh 把同一份 stdin JSON 再喂给 ccstatusline 取上下文占比
    # npm -g 前缀由 dev 组改成了 ~/.local, 所以免 sudo 且判存走绝对路径
    # (pyinfra 的非登录 shell 里 PATH 未必含 ~/.local/bin, command -v 会误判).
    # 单独只跑 claude 组时前缀可能还没配, 那就退回 npm 的默认前缀, 装不上会
    # 报错而不是静默装错地方 —— 正常按顺序跑全量部署没这个问题
    server.shell(
        name="全局装 ccstatusline",
        commands=[f'test -x "{home}/.local/bin/ccstatusline" || npm install -g ccstatusline'],
    )

    for filename in ("statusline-command.sh", "statusline-wrapper.sh"):
        files.put(
            name=f"放 {filename}",
            src=f"files/common/claude/{filename}",
            dest=f"{home}/.claude/{filename}",
            mode="755",
        )

    files.put(
        name="放 ccstatusline 配置",
        src="files/common/claude/ccstatusline-settings.json",
        dest=f"{home}/.config/ccstatusline/settings.json",
        mode="644",
    )

    # statusLine, effortLevel, model, autoCompactEnabled, attribution (commit/PR 不署名 Claude), hooks (完成/通知提示音),
    # enabledPlugins + extraKnownMarketplaces (wip-list 插件市场),
    # 项目专属的 autoMode 不放这里 (公开仓库, 且整份覆盖会冲掉), 放各项目自己的 .claude/settings.local.json,
    # env.CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1 (关自动更新/遥测/错误上报/bug 反馈: 走中转时这些直连官方的请求没必要, 国内还容易卡; 代价是要手动 claude update)
    # 不直接写 settings.json: 交给 cc-switch 的通用配置片段, 切 provider 重写 settings.json 时片段会被重新合并进去, 不会丢
    files.put(
        name="放通用配置片段",
        src="files/common/claude/common-snippet.json",
        dest=f"{home}/.cc-switch/common-snippet.json",
        mode="644",
    )
    server.shell(
        name="注入通用配置片段",
        commands=[f"{cc_switch} config common set -a claude --file {home}/.cc-switch/common-snippet.json"],
    )


# memory 组: zram 压缩 swap 的配置. zram 本身就是 swap 设备 (放在内存里, 压缩
# 存储), zstd 下压缩比约 3:1, 半个内存大小的 zram 实际只占约 1/6 物理内存.
# 不另开磁盘 swap: 机器不休眠到硬盘, 且 btrfs 上 swapfile 所在子卷不能快照,
# 还挡部分 balance/resize; 内存真不够时靠 earlyoom 杀进程, 而不是换页到盘上卡死
ZRAM_CONF = """[zram0]
zram-size = ram / 2
compression-algorithm = zstd
swap-priority = 100
"""

# swappiness 默认 60 是按磁盘 swap 调的. 换到 zram 后换页只是内存里压缩/解压,
# 比丢 page cache 后再读盘便宜, 内核文档建议此时设到 100 以上 (上限 200).
# page-cluster=0: 每次只换入 1 页而不是预读 8 页, 预读是给磁盘寻道摊成本用的,
# 对 zram 只是白解压
SWAP_SYSCTL = """vm.swappiness = 150
vm.page-cluster = 0
"""


@deploy("内存")
def memory():
    """zram 压缩 swap + earlyoom, 不开磁盘 swap.

    起因: 20 核满并行编 libjxl 时内存打满, 无 swap 时内核 OOM killer 出手前
    整机卡死. earlyoom 在可用内存与 swap 都低于 10% 时先杀最大进程.
    """
    pacman.packages(
        name="装 zram-generator 与 earlyoom",
        packages=["zram-generator", "earlyoom"],
        _sudo=True,
    )

    zram = files.put(
        name="放 zram-generator 配置",
        src=StringIO(ZRAM_CONF),
        dest="/etc/systemd/zram-generator.conf",
        mode="644",
        add_deploy_dir=False,
        _sudo=True,
    )

    # zram 设备由 generator 在开机时生成 unit, 没有 enable 一说; 首次装好后
    # daemon-reload 让 generator 跑一次, 再起服务就能马上用上, 不必重启.
    # 配置改了也不 restart: 停服务要先 swapoff, 若 zram 里已换出几个 G 会很慢,
    # 甚至因内存不够失败. 改动下次开机生效.
    # did_change 是执行期才有结果的, 只能交给 _if, 不能当 daemon_reload= 的值
    systemd.daemon_reload(name="重跑 zram generator", _if=zram.did_change, _sudo=True)
    systemd.service(
        name="启用 zram swap",
        service="systemd-zram-setup@zram0.service",
        running=True,
        _sudo=True,
    )

    files.put(
        name="放 swap 内核参数",
        src=StringIO(SWAP_SYSCTL),
        dest="/etc/sysctl.d/99-swap.conf",
        mode="644",
        add_deploy_dir=False,
        _sudo=True,
    )
    server.shell(
        name="应用 swap 内核参数",
        commands=["sysctl -q -p /etc/sysctl.d/99-swap.conf"],
        _sudo=True,
    )

    systemd.service(name="启 earlyoom", service="earlyoom", enabled=True, running=True, _sudo=True)


# docker 数据目录 → 顶层子卷. timeshift 的 btrfs 模式只快照 @ 与 @home, 排除
# 列表在 btrfs 模式下不生效, 想不进快照只能单独成子卷 (同 @cache @log).
# 不进快照的理由: 删掉的镜像被快照引用着, 要等快照轮转掉才释放空间; 回滚系统
# 时也不该把容器与镜像一起回滚. 代价: docker 卷里的数据 (数据库等) 也失去快照
# 保护, 要另外备份.
# 两个都要: 用 containerd 镜像存储 (docker 29 起默认) 时, 镜像层在系统
# containerd.service 的 /var/lib/containerd, /var/lib/docker 只剩容器与卷.
# 用顶层子卷 + fstab 挂载而不是嵌套子卷: timeshift 回滚会换掉整个 @, 嵌套在
# @ 里的子卷不会跟到新 @ 里, 回滚后目录变空
DOCKER_SUBVOLS = {
    "/var/lib/docker": "@docker",
    "/var/lib/containerd": "@containerd",
}

# 已是挂载点 (拆过子卷, 或手动挂到了别的盘) 就什么都不做. 不是目录或是软链
# 也跳过: 说明 docker 数据已经被手动挪出系统盘 (如 .99 挪到 /data), 不能把
# 别处的数据拷回系统盘. 包里不带这两个目录, 新机器要等 docker 首次启动建出
# 来后, 下次部署才会迁. 否则: 停 docker/containerd → 挂顶层 (subvolid=5) 建子卷 →
# cp --reflink 搬数据 (同盘只复制元数据, 秒完且不多占空间) → 写 fstab →
# 原目录挪开换空目录挂上 → 删原目录 → 把停掉的服务再拉起来 (原来没跑的不拉).
# 子卷建在父目录所在的 btrfs 上 (即根), fstab 挂载选项沿用该挂载点那行 (去掉
# 其中的 subvol/subvolid), 与 @cache @log 一致.
# 中断后重跑: 原目录在挂好之前一直保留 (挪开的叫 .pre-subvol, 重跑先挪回来),
# 没挂上的半成品子卷删了重建, 所以不会丢数据.
# 停服务要分两步, 先 dockerd 后 containerd: 一起停时 containerd 可能先没了,
# dockerd 停不掉容器; containerd.service 又是 KillMode=process, 不杀 shim, 容器
# 成了孤儿还挂着 rootfs/overlayfs/<id>, cp 钻进去 reflink 报 Invalid
# cross-device link (.102 上踩过). 停完再查一遍目录下没有挂载才拷, cp -x 再兜底
SUBVOL_MIGRATE_SCRIPT = r"""set -eu
P={path} S={subvol}
old="$P.pre-subvol"
if mountpoint -q "$P"; then rm -rf "$old"; exit 0; fi
if [ -d "$old" ]; then rmdir "$P" 2>/dev/null || true; mv -T "$old" "$P"; fi
if awk -v p="$P" '$1 !~ /^#/ && $2 == p {{f=1}} END {{exit !f}}' /etc/fstab; then
    mkdir -p "$P"; systemctl daemon-reload; mount "$P"; exit 0
fi
if [ -L "$P" ] || [ ! -d "$P" ]; then
    echo "$P 不是系统盘上的目录, docker 数据已不在系统盘, 跳过" >&2; exit 0
fi
units=$(systemctl list-units --state=active --plain --no-legend docker.socket docker.service containerd.service | awk '{{print $1}}')
systemctl stop docker.socket docker.service
systemctl stop containerd.service
if findmnt -rn -o TARGET | grep -q "^$P/"; then
    echo "$P 下还有挂载 (容器没停干净), 不迁:" >&2
    findmnt -rn -o TARGET | grep "^$P/" >&2
    [ -z "$units" ] || systemctl start $units
    exit 1
fi
parent=$(dirname "$P")
src=$(findmnt -no SOURCE -T "$parent" | sed 's/\[.*//')
uuid=$(findmnt -no UUID -T "$parent")
mnt=$(findmnt -no TARGET -T "$parent")
opts=$(awk -v m="$mnt" '$1 !~ /^#/ && $2 == m {{print $4}}' /etc/fstab | sed -E 's/(^|,)subvol(id)?=[^,]*//g; s/^,//')
top=$(mktemp -d)
# 中途失败时卸掉顶层挂载. 只在失败时有事可做, 每条都要 || true: trap 里
# 也受 set -e 管, 正常路径上顶层已卸, umount 失败会把退出码改成 1
trap 'umount "$top" 2>/dev/null || true; rmdir "$top" 2>/dev/null || true' EXIT
mount -o subvolid=5 "$src" "$top"
[ -e "$top/$S" ] && btrfs subvolume delete "$top/$S"
btrfs subvolume create "$top/$S"
cp -ax --reflink=always "$P/." "$top/$S/"
chmod --reference="$P" "$top/$S"
umount "$top"
echo "UUID=$uuid $P btrfs subvol=/$S${{opts:+,$opts}} 0 0" >> /etc/fstab
[ -e "$P" ] && mv -T "$P" "$old"
mkdir -p "$P"
systemctl daemon-reload
mount "$P"
rm -rf "$old"
[ -z "$units" ] || systemctl start $units
"""


def _root_is_btrfs(what: str) -> bool:
    """根分区是不是 btrfs. 不是就打 warning 说明跳过了什么."""
    root = host.get_fact(Mounts).get("/")
    if root and root["type"] == "btrfs":
        return True
    logger.warning(f"{host.name}: 根分区不是 btrfs, 跳过{what}")
    return False


# 内核 6.11 起自带的 btrfs 自动回收: data 块组用得够空时由内核自己 relocate
# 回收, 盘越满越积极. 默认关. 用 tmpfiles 在每次开机时写 sysfs, glob 匹配所有
# 已挂载的 btrfs, 免得按 UUID 一台台写. 内核太老没有这个文件时 glob 匹配不到,
# 静默跳过
BTRFS_RECLAIM_TMPFILES = "w /sys/fs/btrfs/*/allocation/data/dynamic_reclaim - - - - 1\n"


# timeshift 要的配置项. 值一律是字符串, timeshift 自己就这么存.
# 只留 daily 2 份, 其余级别全关且 count 设 0: timeshift 的 auto_remove 不看
# 级别开没开, 只按 count 摘标签, 摘光标签的快照被删, 所以 count 0 会把以前
# 开着时留下的 B/H/W/M 快照也清掉.
# 带注释的快照 (如 timeshift-autosnap 的 "created before upgrade") 不归
# auto_remove 管, 由 autosnap 自己按 maxSnapshots 轮转.
# backup_device_uuid 运行时填根分区 UUID: btrfs 模式快照只能放在根所在的那个
# btrfs 上
TIMESHIFT_SETTINGS = {
    "parent_device_uuid": "",
    "do_first_run": "false",
    "btrfs_mode": "true",
    "include_btrfs_home_for_backup": "true",
    "include_btrfs_home_for_restore": "false",
    "stop_cron_emails": "true",
    "schedule_daily": "true",
    "count_daily": "2",
    "schedule_hourly": "false",
    "count_hourly": "0",
    "schedule_weekly": "false",
    "count_weekly": "0",
    "schedule_monthly": "false",
    "count_monthly": "0",
    "schedule_boot": "false",
    "count_boot": "0",
}

# timeshift 运行时会整份重写 timeshift.json (格式, 键序, snapshot_size 等),
# 不能 files.put 整份覆盖, 用 jq 只合并上面这些键. 已全部一致就不动.
# 还没配过 timeshift 时 timeshift.json 不存在, 以包自带的 default.json 为底.
# default.json 里有旧键 include_btrfs_home="false", timeshift 读配置时只要它在
# 就优先用它、忽略 include_btrfs_home_for_backup, 不删 /home 就不进快照
TIMESHIFT_SCRIPT = r"""set -e
f=/etc/timeshift/timeshift.json
src=$f; [ -f "$f" ] || src=/etc/timeshift/default.json
want=$(jq -c --arg u "$(findmnt -no UUID /)" '. + {backup_device_uuid: $u}' <<'EOF'
{settings}
EOF
)
fix='. * $w | del(.include_btrfs_home)'
[ -f "$f" ] && jq -e --argjson w "$want" "($fix) == ." "$f" >/dev/null && exit 0
jq --argjson w "$want" "$fix" "$src" > "$f.tmp" && mv "$f.tmp" "$f"
"""

# timeshift 只在 GUI 里保存设置时才生成这个 cron 文件, 新机器直接写 json 不会
# 有, 这里照它的原样写 (内容与 timeshift 生成的逐字一致, 免得来回改).
# 它每小时跑 --check, 到点了才真打快照
TIMESHIFT_CRON = """SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin
MAILTO=""

0 * * * * root timeshift --check --scripted
"""


@deploy("存储")
def storage():
    """让系统盘别爆: docker 数据迁独立子卷, btrfs 自动回收与 scrub, timeshift 只留 2 份.

    三件是一套: timeshift 快照会钉住 @ 里删掉的数据 (所以 docker 要挪出 @, 快照
    要少留), 数据删了之后 data 块组又要靠内核回收才能还给新分配.

    起因: data 块组分配满了但里面很空 (删快照后常见), 块组分不出来, 报盘满.
    不装 btrfsmaintenance: 它定时全盘跑 balance, IO 比内核按需回收重.
    """
    if not _root_is_btrfs("存储组"):
        return

    # 先迁 docker, 再配 timeshift: 迁完之后的快照就不再带 docker 数据了
    for path, subvol in DOCKER_SUBVOLS.items():
        server.shell(
            name=f"{path} 迁到子卷 {subvol}",
            commands=[SUBVOL_MIGRATE_SCRIPT.format(path=path, subvol=subvol)],
            _sudo=True,
        )

    reclaim = files.put(
        name="放 btrfs 自动回收 tmpfiles",
        src=StringIO(BTRFS_RECLAIM_TMPFILES),
        dest="/etc/tmpfiles.d/btrfs-reclaim.conf",
        mode="644",
        add_deploy_dir=False,
        _sudo=True,
    )
    server.shell(
        name="立即开启 btrfs 自动回收",
        commands=["systemd-tmpfiles --create /etc/tmpfiles.d/btrfs-reclaim.conf"],
        _if=reclaim.did_change,
        _sudo=True,
    )

    # scrub 校验数据块校验和, 查静默损坏, 与空间无关. `-` 是 / 的 systemd 转义,
    # / 与 /home 在同一个 btrfs 上, 一个就够
    systemd.service(
        name="开每月 btrfs scrub",
        service="btrfs-scrub@-.timer",
        enabled=True,
        running=True,
        _sudo=True,
    )

    # cronie 驱动上面的 cron 文件; jq 改 json
    pacman.packages(name="装 timeshift", packages=["timeshift", "cronie", "jq"], _sudo=True)

    server.shell(
        name="配置 timeshift",
        commands=[TIMESHIFT_SCRIPT.replace("{settings}", json.dumps(TIMESHIFT_SETTINGS))],
        _sudo=True,
    )

    files.put(
        name="放 timeshift cron",
        src=StringIO(TIMESHIFT_CRON),
        dest="/etc/cron.d/timeshift-hourly",
        mode="644",
        add_deploy_dir=False,
        _sudo=True,
    )
    # boot 级别关了, 删掉以前开着时留下的开机快照任务
    files.file(name="删 timeshift 开机快照任务", path="/etc/cron.d/timeshift-boot", present=False, _sudo=True)

    systemd.service(name="启 cronie", service="cronie", enabled=True, running=True, _sudo=True)


# 组名注册. deploy.py 按 only/skip 过滤
GROUPS = {
    "pacman": pacman_setup,
    "cli": cli,
    "dev": dev,
    "input": input_method,
    "docker": docker_setup,
    "memory": memory,
    "storage": storage,
    "browser": browser,
    "apps": apps,
    "sddm": sddm_x11,
    "claude": claude_tools,
}
