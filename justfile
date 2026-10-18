# system-provisioner justfile

# 远程个人机的 SSH 用户, 可在命令行覆盖: just user=leo personal <ip>
user := "naviai"

# 个人机 (默认本地; 传 IP 或 hostname 则走 SSH)
# host 必须是 pyinfra 的第一个位置参数: 写在 deploy.py 后面会被当成第二个操作,
# pyinfra 就在 deploy 上下文外 import deploy.py, host.data 不存在
personal host="@local" *args:
    pyinfra {{host}} deploy.py --data profile=personal {{ if host == "@local" { "" } else { "--user " + user + " --ssh-password-prompt --use-sudo-password" } }} {{args}}

# 公司机 (SSH, 需传 IP 或 hostname)
# 不给 --sudo: 提权范围由 deploy.py 与各层的 _sudo 标记掌控.
# --use-sudo-password 只是声明提权时需要密码
company host *args:
    pyinfra {{host}} deploy.py --data profile=company --user naviai --ssh-password-prompt --use-sudo-password {{args}}

# 语法检查 (对 manjarolinux/base 容器跑 --dry)
check:
    pyinfra @docker/manjarolinux/base deploy.py --data profile=personal --dry

# 列出所有组
groups:
    @echo "common: pacman cli dev input docker apps browser im wps sddm claude"
    @echo "personal: zsh git python wakatime clang aria2 kvantum graphics media latex office extras fonts localbin remote robotics disk"
    @echo "company: placeholder"
