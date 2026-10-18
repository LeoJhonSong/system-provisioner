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

# 个人机只跑 zsh 和 cli 组
just personal only=zsh,cli

# 个人机跳过 latex 和 media 组
just personal skip=latex,media

# 公司机 (传 IP 或 hostname, 会提示输 SSH 密码和 sudo 密码)
just company 192.168.2.99

# 语法检查 (对 Docker 容器跑 --dry, 不真执行)
just check

# 列出所有组
just groups
```

## 组名清单

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
- `claude`: claude-code (官方脚本), cc-switch-cli-git, claude-history

### personal 层
- `zsh`: oh-my-zsh, pkgfile, Shell-Scripts, `~/.config/zsh` 软链
- `git`: user.name (hostname), user.email, credential.helper
- `python`: pyenv, `.pythonrc.py`
- `wakatime`: wakatime-cli, `.wakatime.cfg`
- `clang`: clang, bear, `.clang-format`
- `aria2`: 配置软链
- `kvantum`: kvantum + kvantum-qt5, Plasma widgetStyle 设为 kvantum
- `graphics`: drawio, gimp, inkscape, blender
- `media`: vlc, handbrake, kdenlive, wine, davinci-resolve, deadbeef
- `latex`: texlive 全套
- `office`: zotero, onedrive, linuxqq, zoom
- `extras`: github-desktop, 录屏工具, 串口工具, samba, filezilla
- `disk`: Windows 卷挂载

### company 层
- `placeholder`: 占位 (空)

## 后置条件

- zsh 作为默认 shell (需手动 `chsh -s /bin/zsh`)
- `~/.zshrc` 为本机私有配置, 仓库不跟踪; `~/.config/zsh/default.zsh` 为同步配置
- AUR 包构建失败不中断部署, 仅记 warning
- yay `config.json` 只改 `removemake` 和 `provides` 两键, 其余保持 yay 自己写的值

## 注意事项

- `.wakatime.cfg` 里 `api_key` 是真实值且仓库 PUBLIC, 等同已泄露. 用户确认接受
- 部署账号需在 wheel 组 (Manjaro 默认如此), sudo 密码由命令行传入
- 免密 sudoers 规则限定 `/usr/bin/pacman`, 但 pacman 能执行安装脚本和装本地包, 等同无密码 root. 这是 yay 无人值守的代价: yay 内部自调 `sudo pacman -U`, 那个子进程拿不到 pyinfra 的 askpass
- `buildDir` 在用户 `~/.cache/yay`, 不同用户名机器间不共享缓存

