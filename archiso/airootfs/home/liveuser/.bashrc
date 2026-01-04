#
# ~/.bashrc
#

# If not running interactively, don't do anything
[[ $- != *i* ]] && return

alias ls='ls --color=auto'
alias grep='grep --color=auto'
PS1='[\u@\h \W]\$ '

# Hijack shutdown commands to show feedback prompt
alias shutdown='~/.config/hypr/scripts/shutdown_script.py'
alias poweroff='~/.config/hypr/scripts/shutdown_script.py'
