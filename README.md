# system-provisioner

个人机与公司机的系统配置, pyinfra 实现.

## 架构

- **三层**: `common` (两台都要) / `personal` (仅个人机) / `company` (仅公司机)
- **profile 区分**: 个人机 `@local` 跑 common+personal, 公司机 SSH 跑 common+company
- **分组执行**: 每层内任务切成命名组 (如 `zsh` `docker` `latex`), 可用 `only=` / `skip=` 选择性执行

## 前置条件

- 控制端 (跑 pyinfra 的机器): 已装 `pyinfra` `just`
- 目标机: Manjaro, SSH 可达 (公司机), 或就是控制端自己 (个人机)

## 用法

```sh
# 个人机全量
just personal

# 远程个人机 (传 IP 或 hostname, 会提示输 SSH 密码和 sudo 密码)
just personal 192.168.2.101

# 远程个人机用户名不是 naviai 时
just user=leo personal 192.168.2.101

# 个人机只跑 zsh 和 cli 组
just personal @local --data only=zsh,cli

# 个人机跳过 latex 和 media 组
just personal @local --data skip=latex,media

# 公司机 (传 IP 或 hostname, 会提示输 SSH 密码和 sudo 密码)
just company 192.168.2.99

# 语法检查 (对 Docker 容器跑 --dry, 不真执行)
just check

# 列出所有组
just groups
```

## 组名清单

执行顺序: 先按 `deploy.py` 的 `PRIORITY` 跑 `pacman dev browser input claude im wps office`, 好让部署没跑完就能开始干活; 其余组随后按下列顺序跑.

### common 层
- `pacman`: 中国镜像源, 系统升级, yay 与 yay 配置, pacman 免密 sudoers
- `cli`: tmux, bat, yazi, fd, fzf, nmap, curl, wget, git-lfs, jq, yq
- `dev`: base-devel, gdb, cmake, nodejs/npm, jdk, uv (含 uvx), just, ruff, github-cli, pip/npm 镜像, npm 全局前缀改到 `~/.local` (免 sudo)
- `input`: fcitx5 全套, xorg-xhost, `.xprofile`, 拼音输入法 + 左 Shift 切换
- `docker`: docker + compose, 服务自启, 用户入组
- `apps`: VSCode, Typora, Snipaste, simplescreenrecorder, vlc, handbrake, rar, plasma-x11-session
- `browser`: Edge
- `im`: 微信/飞书/腾讯会议
- `wps`: WPS 国内版全家
- `sddm`: SDDM 默认 X11 session (很多软件需要 X11)
- `claude`: claude-code (官方脚本), cc-switch-cli (官方脚本), claude-history, 状态栏 (ccstatusline + git 信息)

### personal 层
- `zsh`: oh-my-zsh, pkgfile, Shell-Scripts, 部署仓库 clone 到 `~/projects`, `.zshrc` 骨架 (非本仓库所写的先备份再重写)
- `git`: user.name (hostname), user.email, credential.helper
- `python`: pyenv, pyenv-virtualenv, tk (pyenv 编 Python 时 tkinter 需要), `.pythonrc.py`
- `wakatime`: wakatime-cli, `.wakatime.cfg`
- `clang`: clang, bear, `.clang-format`
- `aria2`: 配置软链
- `kvantum`: kvantum + kvantum-qt5, Plasma widgetStyle 设为 kvantum
- `graphics`: drawio, gimp, inkscape, blender
- `media`: kdenlive, wine, audiorelay (davinci-resolve-studio 需手动下载安装包, 代码里只留注释)
- `latex`: texlive 全套
- `office`: zotero, onedrive, linuxqq, zoom
- `extras`: github-desktop, kooha, screenkey, 串口工具, samba, filezilla, appimagelauncher
- `fonts`: FiraCode Nerd Font
- `localbin`: `~/.local/bin` 自写脚本 (dde-file-manager 转 dolphin, snipaste-launcher), dev-browser (npm -g)
- `remote`: anydesk, rustdesk, todesk, clash-verge-rev, openvpn3, frpc, NetworkManager VPN 插件 (openconnect/vpnc/openvpn/l2tp)
- `robotics`: foxglove, python-rosbags
- `disk`: Windows 卷挂载

未纳入部署、按需手装的包见 [OPTIONAL_PACKAGES.md](OPTIONAL_PACKAGES.md). 字体阿里巴巴普惠体, Operator Mono 无包, 是手动放进 `~/.local/share/fonts` 的, 不在仓库里.

### company 层
- `placeholder`: 占位 (空)

## 后置条件

- zsh 作为默认 shell (需手动 `chsh -s /bin/zsh`)
- `~/.zshrc` 为本机私有配置, 仓库不跟踪; `~/projects/system-provisioner/files/personal/zsh/default.zsh` 为同步配置, 由 `.zshrc` 在 manjaro 配置之后、私有配置之前 source
- AUR 包构建失败不中断部署, 仅记 warning
- yay `config.json` 只改 `removemake` 和 `provides` 两键, 其余保持 yay 自己写的值

## 注意事项

- `.wakatime.cfg` 里 `api_key` 是真实值且仓库 PUBLIC, 等同已泄露. 用户确认接受
- 部署账号需在 wheel 组 (Manjaro 默认如此), sudo 密码由命令行传入
- 免密 sudoers 规则限定 `/usr/bin/pacman`, 但 pacman 能执行安装脚本和装本地包, 等同无密码 root. 这是 yay 无人值守的代价: yay 内部自调 `sudo pacman -U`, 那个子进程拿不到 pyinfra 的 askpass
- `buildDir` 在用户 `~/.cache/yay`, 不同用户名机器间不共享缓存

