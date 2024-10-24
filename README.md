# dotfiles

This directory contains the dotfiles for my systems

## Requirements

Ensure you have the following installed on your system

### For MacOS
#### Settings:
```
System Preferences -> Privacy -> Full Disk Access -> Terminal
```
#### Terminal Commands:
```
brew install git stow
${tty_bold}softwareupdate --install-rosetta${tty_reset}
```

### For Fedora

```
yum install git stow
```

## Installation

First, check out the dotfiles repo in your $HOME directory using git

```
$ git clone git@github.com:FullHavocJosh/dotfiles.git
$ cd dotfiles
$ stow .
```

