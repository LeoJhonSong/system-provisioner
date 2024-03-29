# README

A playbook to set up my PC/board/server of different Linux distributions (mainly Manjaro and Debian-based), ready for work in one click 🍻


## Precondition

### Install dependencies

```shell
sudo pacman-mirrors -i -c China -m rank
sudo pacman -Syy
sudo pacman -S ansible
```

### Install required modules

- [community.general collection](https://galaxy.ansible.com/community/general) needed for git_config, pacman and npm modules **in the desktop role**. It is very likely that you already have this collection installed if ansible is installed.
- [kewlfft.aur](https://github.com/kewlfft/ansible-aur) needed to manage packages from AUR, **in the desktop role**.

To install them from Ansible Galaxy, run `ansible-galaxy collection install -r ./requirements.yaml`, or `ansible-galaxy collection install kewlfft.aur` to just install kewlfft.aur.

### proxy

To run from localhost in China, install [ShellClash](https://github.com/juewuy/ShellClash) or other proxy client and start it.

## Usage

```sh
# deploy all tasks to all hosts in hosts
ansible-playbook site.yaml
# apply everything but disk mounting and general softwares installing tasks
ansible-playbook --skip-tags disk,softwares
# only apply to board group in hosts
ansible-playbook site.yaml --limit=board
# list matching hosts under current limits and do nothing else
ansible-playbook site.yaml --limit=board --list-hosts
# only apply disk mounting tasks to localhost via local connection (not ssh connection)
ansible-playbook site.yaml -l localhost --tags disk --connection=local
```

## Postcondition

- check **Hardware clock in local time zone** in `Manjaro Settings Manager > Time and Date`

- set shortcuts in system settings

- [set proxy for onedrive](https://github.com/abraunegg/onedrive/blob/master/docs/USAGE.md#access-onedrive-service-through-a-proxy). Edit systemd service of onedrive with `sudo -e /usr/lib/systemd/user/onedrive.service` and add following two lines under **[Service]** section:

  ```sh
  Environment="HTTP_PROXY=http://127.0.0.1:7890"
  Environment="HTTPS_PROXY=http://127.0.0.1:7890"
  ```

## Tips

To run a single task on managed nodes as check mode to try out what exactly will happen, use this:

```sh
ansible <nodes> -m <module> -a '{"opt1": "val1", "opt2": "val2"}' -C
```

Here is an example and its output:

```sh
# install nvidia-settings using module community.general.pacman under check mode
ansible localhost -m community.general.pacman -a '{"pkg":"nvidia-settings", "state":"present"}' -C
```

```sh
[WARNING]: No inventory was parsed, only implicit localhost is available
localhost | CHANGED => {
    "changed": true,
    "msg": "Would have installed 5 packages",
    "packages": [
        "egl-wayland",
        "eglexternalplatform",
        "libxnvctrl",
        "nvidia-settings",
        "nvidia-utils"
    ]
}
```
