#!/bin/zsh
# check-fork-paths.sh common|refs — guard the switch from upstream lumo-tamer to the fullhavoc fork.
#   common: the defaults in lumo-common.sh / provision-tamer.sh point at the fork and the host patch survives.
#   refs:   no tracked file still hardcodes the old upstream checkout path.
set -u
ROOT=${0:A:h:h:h}

case ${1:-} in
common)
	fail=0
	grep -q '^LUMO_TAMER_DIR=.*lumo-tamer-fullhavoc' "$ROOT/.config/lumo/lumo-common.sh" ||
		{
			print -u2 "FAIL: lumo-common.sh LUMO_TAMER_DIR default is not lumo-tamer-fullhavoc"
			fail=1
		}
	grep -q 'fullhavocjosh/lumo-tamer-fullhavoc\.git' "$ROOT/.config/lumo/provision-tamer.sh" ||
		{
			print -u2 "FAIL: provision-tamer.sh TAMER_REPO default is not the fullhavocjosh fork"
			fail=1
		}
	grep -q 'LUMO_TAMER_HOST' "$ROOT/.config/lumo/provision-tamer.sh" ||
		{
			print -u2 "FAIL: provision-tamer.sh lost the LUMO_TAMER_HOST perl patch"
			fail=1
		}
	exit $fail
	;;
refs)
	cd "$ROOT" || exit 1
	matches=$(grep -rEn '(~|HOME"?|home\})/lumo-tamer([^-]|$)' \
		.config/lumo/*.sh \
		.config/aistack/aidev_lib.py \
		.pi/agent/extensions/lumo-first.ts \
		.zshrc_aliases \
		.zshrc_functions_ai \
		nix-modules/macos/lumo.nix)
	if [[ -n $matches ]]; then
		print -r -- "$matches"
		exit 1
	fi
	exit 0
	;;
*)
	print -u2 "usage: ${0:t} common|refs"
	exit 2
	;;
esac
