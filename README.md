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

currently only [kewlfft.aur](https://github.com/kewlfft/ansible-aur) needed, to manage packages from AUR.

```shell
ansible-galaxy collection install -r requirements.yaml
```

### proxy

Install shellclash or other proxy client and start it.

## Usage

```sh
# deploy
ansible-playbook site.yaml
# skip disk mounting and general softwares installing tasks when debugging
ansible-playbook --skip-tags disk,softwares
# only apply on board group
ansible-playbook site.yaml --limit=board
```

## Postcondition

- check **Hardware clock in local time zone** in `Manjaro Settings Manager > Time and Date`
- set shortcuts in system settings