# Path to your oh-my-zsh installation.
if [[ -f ~/.oh-my-zsh/oh-my-zsh.sh ]]; then
    export ZSH=~/.oh-my-zsh

    source $(dirname $0)/antigen.zsh  # require antigen.sh and this file in same directory
    # Load the oh-my-zsh's library.
    antigen use oh-my-zsh
    # Bundles from the default repo (robbyrussell's oh-my-zsh).
    antigen bundle command-not-found
    antigen bundle colored-man-pages
    antigen bundle sudo
    # custom plugins
    antigen bundle zsh-users/zsh-syntax-highlighting
    antigen bundle zsh-users/zsh-autosuggestions
    # copy wakatime configuration file if not exist
    [[ -f $HOME/.wakatime.cfg ]] && antigen bundle sobolevn/wakatime-zsh-plugin
    # Load the theme.
    antigen theme romkatv/powerlevel10k
    # Tell Antigen that you're done.
    antigen apply
    source $ZSH/oh-my-zsh.sh
fi

# colored GCC warnings and errors
export GCC_COLORS='error=01;31:warning=01;35:note=01;36:caret=01;32:locus=01:quote=01'

# set to vi-mode learn more: http://zsh.sourceforge.net/Doc/Release/Zsh-Line-Editor.html
bindkey -v
# set default editor for softwares. e.g. git
export EDITOR=vim

# add local bin to PATH
export PATH=$HOME/.local/bin/:$PATH

# Set personal aliases, overriding those provided by oh-my-zsh libs, plugins,
# and themes. For a full list of active aliases, run `alias`.
alias exp='export PATH=$(pwd):$PATH'
alias lt='ls --tree'
alias l='ls -a'
alias ll='ls -al'
alias ccze='ccze -A'
command -v bat &> /dev/null && alias cat='bat'  # if bat exist, set as cat's alias
command -v lsd &> /dev/null && alias ls='lsd'
alias p='python'

# fzf config and initial
if command -v fzf &> /dev/null; then
    export FZF_DEFAULT_COMMAND="fd --type f --hidden --follow"
    # export FZF_DEFAULT_COMMAND="fd --type f --hidden --follow --exclude $FD_EXCLUDES"
    export FZF_COMPLETION_TRIGGER=']'
    export FZF_DEFAULT_OPTS='--layout=reverse --info=hidden --marker="✔ " --prompt=" "'
    # Use fd (https://github.com/sharkdp/fd) instead of the default find
    # command for listing path candidates.
    # - The first argument to the function ($1) is the base path to start traversal
    # - See the source code (completion.{bash,zsh}) for the details.
    _fzf_compgen_path() {
        fd --type f --hidden --follow . "$1"
    }
    # Use fd to generate the list for directory completion
    _fzf_compgen_dir() {
        fd --type d --hidden --follow . "$1"
    }
    # (EXPERIMENTAL) Advanced customization of fzf options via _fzf_comprun function
    # - The first argument to the function is the name of the command.
    # - You should make sure to pass the rest of the arguments to fzf.
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
    [[ $- == *i* ]] && source /usr/share/fzf/completion.zsh 2> /dev/null # load auto-completion
    source /usr/share/fzf/key-bindings.zsh # load keybindings
fi

# navi widget install (keybinding: Ctrl-G)
command -v navi &> /dev/null && eval "$(navi widget zsh)"

# pyenv initial
if [ -f ~/.pyenv/bin/pyenv ]; then
    export PYENV_ROOT=$HOME/.pyenv
    export PATH=$PYENV_ROOT/bin:$PATH
    eval "$(pyenv init --path)"
    eval "$(pyenv init -)"
fi

# set user-wide path of RubyGems
if command -v ruby &> /dev/null ; then
    export GEM_HOME="$(ruby -e 'puts Gem.user_dir')"
    export PATH="$PATH:$GEM_HOME/bin"
fi
