export BACKUP_DIR=~/projects/system-provisioner
source $BACKUP_DIR/roles/common/files/zsh/default.zsh

# add scripts to PATH
export PATH=$HOME/projects/Shell-Scripts/:$PATH

# add PYTHONSTARTUP for config of interactive Python
[[ -f $HOME/.pythonrc.py ]] && export PYTHONSTARTUP=$HOME/.pythonrc.py

# proxy
export PROXY=http://127.0.0.1:7890
alias vpn="export http_proxy=$PROXY; export https_proxy=$PROXY"
alias unvpn="unset http_proxy && unset https_proxy"

alias crash="bash /home/leo/local//ShellCrash/menu.sh"
alias clash="bash /home/leo/local//ShellCrash/menu.sh"
export CRASHDIR="/home/leo/local//ShellCrash"