# frp 公网 SSH: 只认密钥的独立入口

经公网 frps 反向穿透 SSH. 2026-10-06 曾把 sshd 的 22 端口直接映射到公网, 密码登录开着, 被爆破入侵. 现方案: sshd 另开一个只监听回环的 2222 入口, 该入口只认密钥, frpc 只转发 2222. 局域网照常走 22, 密码可用.

```
公网 frps:<remotePort> -> frpc -> 127.0.0.1:2222 (sshd, 仅密钥)
局域网 -> 0.0.0.0:22 (sshd, 允许密码)
```

## 端口分配

frps 上每台机器一个 `remotePort`, 代理名也不能重复, 否则后连上的那台会被拒绝.

| 机器 | 代理名 | remotePort |
|---|---|---|
| leo-wj15 (个人机) | `wj15-ssh` | 6001 |
| naviai-ms7e42 (公司机) | `ssh_naviai-msi` | 6002 |

## sshd

`/etc/ssh/sshd_config.d/50-frp-keyonly.conf`:

```
# 局域网照常走 22 (允许密码); frpc 只转发到 127.0.0.1:2222, 该入口只认密钥
Port 22
ListenAddress 0.0.0.0
ListenAddress ::
ListenAddress 127.0.0.1:2222

Match LocalPort 2222
    PasswordAuthentication no
    KbdInteractiveAuthentication no
    AuthenticationMethods publickey
    PermitRootLogin no
```

写完先 `sudo sshd -t` 校验, 通过再 `sudo systemctl restart sshd` (已建立的会话不断). 公网登录用的公钥 (如 LeoTermux) 要加进目标账号的 `~/.ssh/authorized_keys`.

## frpc

`frpc-bin` 自带的 `frpc.service` 用 `LoadCredential` 读 `/etc/frp/frpc.ini`. frpc 按内容识别格式, 文件名是 `.ini` 也可以写 TOML; 或者加 override 改读 `frpc.toml`:

```
# sudo systemctl edit frpc
[Service]
ExecStart=
ExecStart=/usr/bin/frpc -c ${CREDENTIALS_DIRECTORY}/config_toml
```

配置 (token 与服务器地址不入库, 从已配好的机器上抄):

```toml
serverAddr = "<frps 地址>"
serverPort = 7000

auth.method = "token"
auth.token = "<token>"

transport.tls.enable = true

includes = ["/etc/frp/frpc.d/*.toml"]

[[proxies]]
name = "<代理名>"
type = "tcp"
localIP = "127.0.0.1"
localPort = 2222
remotePort = <remotePort>
```

`includes` 必须放在 `[[proxies]]` 之前: 写在后面它会归到那个代理表里, 不生效. `frpc verify -c <文件>` 校验语法, 然后 `sudo systemctl enable --now frpc`.

frps 换 token 或改成强制 TLS 后, 没同步的机器会登录失败, `journalctl -u frpc` 能看到报错.

## 验证

- 公网: `ssh -p <remotePort> <用户>@<frps 地址>` 用密钥能登录
- 同一地址强制密码登录应被拒绝: `ssh -o PubkeyAuthentication=no -p <remotePort> <用户>@<frps 地址>` 报 `Permission denied (publickey)`
