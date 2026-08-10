# force UTF-8 encoding
export LC_ALL=en_US.UTF-8
export LANG=en_US.UTF-8

# omz 初始化. 插件: sudo (Esc Esc 在命令前加 sudo), colored-man-pages, docker
if [[ -f ~/.oh-my-zsh/oh-my-zsh.sh ]]; then
    export ZSH=~/.oh-my-zsh
    export ZSH_THEME=""  # 不加载 omz 自己的主题, p10k 已由 manjaro-zsh-prompt 加载
    plugins=(sudo colored-man-pages docker)
    source $ZSH/oh-my-zsh.sh
fi

# colored GCC warnings and errors
export GCC_COLORS='error=01;31:warning=01;35:note=01;36:caret=01;32:locus=01:quote=01'

# EDITOR 留空: 系统自带 vim 但不纳入管理, 不确保存在
# export EDITOR=vim

# proxy alias: $PROXY 在 ~/.zshrc 里定义 (本机私有)
alias vpn='export http_proxy=$PROXY; export https_proxy=$PROXY'
alias unvpn='unset http_proxy && unset https_proxy'

# add local bin & Shell-Scripts to PATH
export PATH=$HOME/.local/bin/:$HOME/projects/Shell-Scripts/:$PATH

# Set personal aliases
alias exp='export PATH=$(pwd):$PATH'
alias lt='ls --tree'
alias l='ls -a'
alias ll='ls -al'
alias ys='yay -S'
command -v bat &> /dev/null && alias cat='bat --style grid'
command -v lsd &> /dev/null && alias ls='lsd'
alias p='python'

# fzf config
if command -v fzf &> /dev/null; then
    export FZF_DEFAULT_COMMAND="fd --type f --hidden --follow"
    export FZF_COMPLETION_TRIGGER=']'
    export FZF_DEFAULT_OPTS='--layout=reverse --info=hidden --marker="✔ " --prompt=" "'

    _fzf_compgen_path() {
        fd --type f --hidden --follow . "$1"
    }

    _fzf_compgen_dir() {
        fd --type d --hidden --follow . "$1"
    }

    _fzf_comprun() {
        local command=$1
        shift
        case "$command" in
            cd)             fzf "$@" --preview 'lsd --tree {} | head -200' ;;
            export|unset)   fzf "$@" --preview "eval 'echo \$'{}" ;;
            ssh)            fzf "$@" --preview 'dig {}' ;;
            vim)            fzf "$@" --preview 'bat --style=numbers --color=always --line-range :500 {}' ;;
            *)              fzf "$@" ;;
        esac
    }

    [[ $- == *i* ]] && source /usr/share/fzf/completion.zsh 2> /dev/null
    source /usr/share/fzf/key-bindings.zsh
fi

# yazi cd 集成
if command -v yazi &> /dev/null; then
    function y() {
        local tmp="$(mktemp -t "yazi-cwd.XXXXXX")" cwd
        yazi "$@" --cwd-file="$tmp"
        IFS= read -r -d '' cwd < "$tmp"
        [ -n "$cwd" ] && [ "$cwd" != "$PWD" ] && builtin cd -- "$cwd"
        rm -f -- "$tmp"
    }
fi

# pyenv init
if [ -f ~/.pyenv/bin/pyenv ]; then
    export PYENV_ROOT=$HOME/.pyenv
    export PATH=$PYENV_ROOT/bin:$PATH
    eval "$(pyenv init --path)"
    eval "$(pyenv init -)"
fi

