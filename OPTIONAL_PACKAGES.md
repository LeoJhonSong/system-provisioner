# 按需手装的包

旧个人机 (Leo-WJ15) 2026-10 重装前装过、但没放进部署的包. 有的已经不用, 有的
可能 Manjaro KDE 自带. 用到时按名字装: 官方源 `sudo pacman -S <包>`, AUR `yay -S <包>`.

## 开发

| 包 | 来源 | 用途 |
|---|---|---|
| neovim, python-pynvim | 官方 | 编辑器 + Python 插件宿主 |
| micro | 官方 | 简单终端编辑器 |
| lazygit, gitui | 官方 | git 终端 UI |
| ansible, ansible-lint | 官方 | 配置管理 |
| docker-buildx | 官方 | docker buildx 插件 |
| python-pip | 官方 | 系统 Python 的 pip |
| ccusage | AUR | Claude Code 等 CLI 的 token 用量统计 |
| kate-wakatime-git | AUR | Kate 的 WakaTime 插件 |

## 虚拟化

| 包 | 来源 | 用途 |
|---|---|---|
| qemu-full, virt-manager, edk2-ovmf, swtpm | 官方 | QEMU/KVM 虚拟机 (UEFI + TPM, 可跑 Win11). 装完 `sudo systemctl enable --now libvirtd` |
| spice-vdagent | 官方 | 作为虚拟机客户机时的剪贴板/分辨率同步 |

## 网络与远程

| 包 | 来源 | 用途 |
|---|---|---|
| tailscale | 官方 | 组网 VPN. `sudo systemctl enable --now tailscaled && sudo tailscale up`. 远程 SSH 走这个, 不要用 frp 暴露 22 |
| remmina, freerdp | 官方 | RDP/VNC 客户端 |
| sshfs | 官方 | 通过 SSH 挂载远程目录 |
| nfs-utils | 官方 | NFS 客户端/服务端 |
| net-tools | 官方 | ifconfig, netstat 等旧工具 |
| kdeconnect | 官方 | 手机互联 |
| baidunetdisk-bin | AUR | 百度网盘 |

## 系统与硬件

| 包 | 来源 | 用途 |
|---|---|---|
| yt6801-dkms | AUR | **Motorcomm YT6801 有线网卡驱动** (旧机板载网卡). 没它有线网不通, 先连 Wi-Fi 装 |
| tlpui | 官方 | TLP 电源管理 GUI. 需 `tlp` 服务 |
| powertop, acpi, cpupower | 官方 | 功耗诊断, 电池/温度读数, CPU 调频 |
| radeontop, radeon-profile-git (AUR) | 官方/AUR | AMD 显卡占用与调参 |
| htop, fastfetch, neofetch (AUR), inxi | 官方 | 系统信息 |
| usbutils, dmidecode | 官方 | lsusb, 硬件 DMI 信息 |
| sbctl | 官方 | Secure Boot 密钥管理 |
| grub-btrfs, timeshift, timeshift-autosnap-manjaro | 官方 | btrfs 快照进 GRUB 菜单, 升级前自动快照 |
| cronie | 官方 | crontab |
| xilinx-u280-gen3x16-xdma-base | AUR | Xilinx Alveo U280 FPGA 卡的基础平台 (装在 /opt/xilinx) |

## 应用

| 包 | 来源 | 用途 |
|---|---|---|
| freecad | 官方 | 参数化 3D CAD |
| mpv | 官方 | 播放器 |
| deadbeef | AUR | 音乐播放器 |
| yakuake | 官方 | 下拉式终端 |
| pantheon-camera | 官方 | 摄像头 |
| pdftk | 官方 | PDF 合并/拆分 |
| jpegoptim | 官方 | JPEG 压缩 |
| unarchiver | 官方 | unar/lsar 解压 (处理乱码 zip 好用) |
| libdvdcss | 官方 | DVD 解密播放 |
| system-config-printer | 官方 | 打印机配置 |

## 字体

| 包 | 来源 | 用途 |
|---|---|---|
| noto-fonts-emoji | 官方 | 彩色 emoji |
| ttf-inconsolata | 官方 | 等宽字体 |

阿里巴巴普惠体, Operator Mono 没有包, 字体文件备份在移动硬盘
`manjaro-reinstall-2026-10-06/fonts/`, 复制到 `~/.local/share/fonts/` 后 `fc-cache -f`.

## 非包管理器装的东西

| 东西 | 装法 |
|---|---|
| Flutter SDK (`~/local/flutter`) | 官网下载解压; `flutter_rust_bridge_codegen` 用 `cargo install flutter_rust_bridge_codegen` |
| ossutil, bcecmd, lakebase-client | 各自官网下载二进制放 `/usr/local/bin`. 旧机 AK/SK 视为已泄露, 用新的 |
| isaacsim-webrtc-streaming-client, OpenTypeless | AppImage, 放 `~/Applications` |
| VS Code Remote Tunnel | VS Code 里 "Turn on Remote Tunnel Access", 会生成用户服务 code-tunnel.service |
