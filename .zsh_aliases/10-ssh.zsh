alias sshmacbook='ssh -i ~/.ssh/id_ed25519 havoc@macbookm2pro.rollet.family'
alias sshg14='ssh -i ~/.ssh/id_ed25519 root@Joshs-G14.rollet.family'
alias sshazeroth='ssh -i ~/.ssh/id_ed25519 root@azerothcore.rollet.family'
alias sshtestazeroth='ssh -i ~/.ssh/id_ed25519 root@testing-azerothcore.rollet.family'
alias sshmini='ssh -i ~/.ssh/id_ed25519 havoc@macminim1.rollet.family'
alias sshtruenas='ssh -i ~/.ssh/id_ed25519 admin@truenas.rollet.family'
alias ssh6rx26x1='ssh -i ~/.ssh/id_ed25519 havoc@6rx26x1.rollet.family'
alias sshcaitsg14='ssh -i ~/.ssh/id_ed25519 nesheri@Caits-G14.rollet.family'
alias sshxps13='ssh -i ~/.ssh/id_ed25519 havoc@xps13.rollet.family'
alias sshopnsense='ssh -i ~/.ssh/id_ed25519 root@opnsense.rollet.family'
alias ssh705g4='ssh -i ~/.ssh/id_ed25519 havoc@705g4.rollet.family'
alias ssh4kfjsn2='ssh -i ~/.ssh/id_ed25519 havoc@4kfjsn2.rollet.family'
alias ssh2fgjsn2='ssh -i ~/.ssh/id_ed25519 havoc@2fgjsn2.rollet.family'
alias sshk3sworkervm0='ssh -i ~/.ssh/id_ed25519 havoc@k3sworkervm0.rollet.family'
alias sshk3sworkervm1='ssh -i ~/.ssh/id_ed25519 havoc@k3sworkervm1.rollet.family'
alias sshha='ssh -i ~/.ssh/id_ed25519 root@homeassistant.rollet.family'
alias sshsteamdeck='ssh -i ~/.ssh/id_ed25519 deck@joshs-steamdeck.rollet.family'
alias sshnovadeck='ssh -i ~/.ssh/id_ed25519 armada@novadeck.rollet.family'
# NOBARA_LAPTOP_IP has no stable DNS hostname (DHCP reservation only) -- set it
# in the local, gitignored ~/.zshrc_envvars (not _insecure, since it's still an
# internal LAN IP): export NOBARA_LAPTOP_IP="192.168.144.35"
alias sshnobaralaptop='ssh -i ~/.ssh/id_ed25519 havoc@${NOBARA_LAPTOP_IP}'

# macOS Screen Sharing (VNC) to MacMiniM1; Screen Sharing.app asks for the password
alias vncmini='open vnc://havoc@macminim1.rollet.family'

# Pulls the KRDP username/password from Doppler (fullhavocjosh/root_nobaralaptop)
# at run time instead of hardcoding them, then pipes the password to sdl-freerdp
# via /from-stdin so it never appears in argv/process list/shell history.
rdpnobaralaptop() {
  local user pass
  user=$(doppler secrets get KRDP_USERNAME --project fullhavocjosh --config root_nobaralaptop --plain) || return 1
  pass=$(doppler secrets get KRDP_PASSWORD --project fullhavocjosh --config root_nobaralaptop --plain) || return 1
  printf '%s\n' "$pass" | sdl-freerdp /v:${NOBARA_LAPTOP_IP} "/u:$user" /from-stdin /cert:ignore /dynamic-resolution /size:1920x1080
}

