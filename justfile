# system-provisioner justfile

# 个人机 (本地)
personal *args:
    pyinfra @local deploy.py --data profile=personal --data proxy=http://127.0.0.1:7890 {{args}}

# 公司机 (SSH, 需传 IP 或 hostname)
company host *args:
    pyinfra {{host}} deploy.py --data profile=company --user naviai --ssh-password-prompt --use-sudo-password {{args}}

# 语法检查 (对 manjarolinux/base 容器跑 --dry)
check:
    pyinfra @docker/manjarolinux/base deploy.py --data profile=personal --dry

# 列出所有组
groups:
    @echo "common: pacman cli dev input docker apps sddm claude"
    @echo "personal: zsh git python wakatime clang aria2 graphics media latex office extras disk"
    @echo "company: placeholder"
