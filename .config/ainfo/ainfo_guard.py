#!/usr/bin/env python3
"""ainfo read-only guard: a Claude Code PreToolUse hook that denies everything not known to be read-only.

ainfo hands this file to Claude with `--settings` (see ainfo_mcp.py), so it only exists for ainfo's own Claude calls;
a plain `claude` run never loads it. Default is DENY: a tool, MCP method or shell command is allowed only when a
rule below says it only reads. Hook input is JSON on stdin; the answer is one JSON line on stdout.

Layers: this hook (tool and command policy), `--disallowedTools` (the same denials, enforced by Claude Code itself)
and a macOS sandbox profile that refuses file writes outside a few cache directories (ainfo_mcp.py).
"""

import configparser
import fnmatch
import json
import os
import re
import shlex
import sys

# ---- built-in tools ---------------------------------------------------------------------------------------------
# Everything else (Edit, Write, MultiEdit, NotebookEdit, WebFetch, WebSearch, Agent, Task, Skill, ...) is denied:
# online research is Lumo's job, and nothing may write.
BUILTIN_ALLOW = {"Read", "Grep", "Glob", "LS", "ToolSearch", "TodoWrite"}
PATH_TOOLS = {
    "Read": ("file_path",),
    "Grep": ("path",),
    "Glob": ("path",),
    "LS": ("path",),
}

# Files Claude must not read: credentials and key material. It is told to ask the user for what it needs from them.
SECRET_GLOBS = [
    ".env", ".env.*", "*.pem", "*.key", "*.p12", "*.pfx", "id_rsa*", "id_ed25519*", "id_ecdsa*",
    "*.tfstate", "*.tfstate.*", "*.tfvars", "*.auto.tfvars", "credentials", "credentials.json", ".netrc",
    ".npmrc", ".pypirc", "kubeconfig", "*.kubeconfig", "hosts.yml", ".zshrc_envvars_insecure",
    ".zshrc_personal", "secrets.yaml", "secrets.yml",
]  # fmt: skip
SECRET_DIRS = {".ssh", ".gnupg", ".aws", ".doppler", ".kube", ".password-store"}


def secret_path(path):
    parts = [x for x in os.path.expanduser(str(path or "")).split(os.sep) if x]
    if any(x in SECRET_DIRS for x in parts):
        return True
    return bool(parts) and any(
        fnmatch.fnmatch(parts[-1].lower(), g) for g in SECRET_GLOBS
    )


# ---- shell commands ---------------------------------------------------------------------------------------------
# One entry per command word. The value is None (any arguments are fine) or a function that gets the arguments and
# returns None when they only read, else the reason they do not.
def no_flags(*bad):
    def check(args):
        for a in args:
            for b in bad:
                if a == b or a.startswith(b + "="):
                    return f"{b} is not allowed"
        return None

    return check


def sed_check(args):
    for a in args:
        if re.match(r"-[a-zA-Z]*i", a) or a.startswith("--in-place"):
            return "sed -i edits files"
        if not a.startswith("-") and (
            re.search(r"(^|[;{}\s])[wWeE]\s*\S", a)
            or re.search(r"s(.)(?:(?!\1).)*\1(?:(?!\1).)*\1[a-zA-Z0-9]*[weWE]", a)
        ):
            return "sed w/e commands write or execute"
    return None


def find_check(args):
    bad = {
        "-exec",
        "-execdir",
        "-ok",
        "-okdir",
        "-delete",
        "-fprint",
        "-fprint0",
        "-fprintf",
        "-fls",
    }
    return next((f"find {a} is not allowed" for a in args if a in bad), None)


def awk_check(args):
    if re.search(r"system\s*\(|getline|print[f]?\b[^;}]*>|\|\s*\"", " ".join(args)):
        return "awk may only print to stdout"
    return None


CURL_FLAGS = {
    "-s", "-S", "-L", "-k", "-I", "-i", "-v", "-f", "-G", "-4", "-6", "-sS", "-sk", "-sL", "-sSL", "-sf",
    "-sfL", "-skL", "--compressed", "--fail", "--insecure", "--location", "--silent", "--show-error",
    "--head", "--get",
}  # fmt: skip
CURL_VALUE_FLAGS = {
    "-H",
    "--header",
    "-m",
    "--max-time",
    "--connect-timeout",
    "--retry",
    "-u",
    "--user",
    "--url",
    "-w",
    "--write-out",
    "--max-redirs",
}


def curl_check(args):
    skip = False
    for i, a in enumerate(args):
        if skip:
            skip = False
        elif a in ("-X", "--request"):
            if i + 1 >= len(args) or args[i + 1].upper() not in ("GET", "HEAD"):
                return "curl may only GET or HEAD"
            skip = True
        elif a.startswith("-"):
            if a in CURL_VALUE_FLAGS:
                skip = True
            elif a not in CURL_FLAGS:
                return (
                    f"curl {a} is not allowed (GET only: no uploads, no output files)"
                )
    return None


GIT_READ = {
    "status", "log", "diff", "show", "blame", "ls-files", "ls-tree", "ls-remote", "rev-parse", "rev-list",
    "describe", "shortlog", "grep", "cat-file", "show-ref", "name-rev", "merge-base", "diff-tree",
    "for-each-ref", "reflog", "count-objects", "check-ignore", "whatchanged", "range-diff", "version",
}  # fmt: skip


def git_check(args):
    a = list(args)
    while a and a[0] in ("-C", "-c", "--no-pager", "--git-dir", "--work-tree"):
        a = a[1:] if a[0] == "--no-pager" else a[2:]
    if not a:
        return "git needs a subcommand"
    sub, rest = a[0], a[1:]
    if sub in GIT_READ:
        if any(
            r == "--output"
            or r.startswith("--output=")
            or r in ("--ext-diff", "--textconv")
            for r in rest
        ):
            return "git option writes a file or runs a program"
        return None
    if sub == "branch":
        if any(
            r
            in (
                "-d",
                "-D",
                "-m",
                "-M",
                "-c",
                "-C",
                "-u",
                "--set-upstream-to",
                "--unset-upstream",
                "--edit-description",
            )
            for r in rest
        ):
            return "git branch may only list"
        return (
            None
            if not [r for r in rest if not r.startswith("-")]
            or "--list" in rest
            or "--contains" in rest
            else "git branch may only list"
        )
    if sub == "tag":
        return (
            None
            if not rest or rest[0] in ("-l", "--list", "-n")
            else "git tag may only list"
        )
    if sub == "remote":
        return (
            None
            if not rest or rest[0] in ("-v", "show", "get-url")
            else "git remote may only list"
        )
    if sub == "config":
        return (
            None
            if rest
            and rest[0] in ("--get", "--get-all", "--list", "-l", "--get-regexp")
            else "git config may only read"
        )
    if sub == "worktree":
        return None if rest[:1] == ["list"] else "git worktree may only list"
    if sub == "stash":
        return (
            None
            if rest[:1] in (["list"], ["show"])
            else "git stash may only list or show"
        )
    return f"git {sub} is not allowed"


GH_READ = {
    "pr": {"view", "list", "diff", "checks", "status"},
    "issue": {"view", "list", "status"},
    "run": {"view", "list"},
    "repo": {"view", "list"},
    "release": {"view", "list"},
    "workflow": {"view", "list"},
    "search": {"prs", "issues", "repos", "code", "commits"},
    "label": {"list"},
    "auth": {"status"},
}


def gh_check(args):
    if args[:1] == ["api"]:
        rest = args[1:]
        for i, r in enumerate(rest):
            if r in ("-X", "--method") and (
                i + 1 >= len(rest) or rest[i + 1].upper() != "GET"
            ):
                return "gh api may only GET"
            if r in ("-f", "-F", "--field", "--raw-field", "--input"):
                return "gh api with fields or input sends data"
        return None
    a = [x for x in args if x not in ("-R", "--repo") and not x.startswith("--repo=")]
    if len(a) < 2:
        return "gh needs a subcommand"
    return (
        None if a[1] in GH_READ.get(a[0], set()) else f"gh {a[0]} {a[1]} is not allowed"
    )


def terraform_check(args):
    a = [x for x in args if not x.startswith("-chdir")]
    if not a:
        return "terraform needs a subcommand"
    if a[0] in ("validate", "show", "output", "providers", "version", "graph"):
        return None
    if a[0] == "fmt":
        return (
            None
            if "-check" in a and "-write=true" not in a
            else "terraform fmt needs -check"
        )
    if a[0] in ("state", "workspace"):
        ok = (["list"], ["show"], ["pull"]) if a[0] == "state" else (["list"], ["show"])
        return None if a[1:2] in ok else f"terraform {a[0]} may only read"
    return f"terraform {a[0]} is not allowed"


def kubectl_check(args):
    a = [x for x in args if not x.startswith("-")]
    if not a:
        return "kubectl needs a subcommand"
    if a[0] in ("get", "describe", "logs") and any(
        x.split("/")[0] in ("secret", "secrets") for x in a[1:3]
    ):
        return "kubectl may not read secrets"
    if a[0] in (
        "get",
        "describe",
        "logs",
        "top",
        "explain",
        "api-resources",
        "api-versions",
        "version",
        "events",
        "cluster-info",
    ):
        return None
    if a[0] == "config":
        return (
            None
            if a[1:2] in (["get-contexts"], ["current-context"])
            else "kubectl config may only list contexts"
        )
    if a[0] == "auth":
        return None if a[1:2] == ["can-i"] else "kubectl auth may only can-i"
    return f"kubectl {a[0]} is not allowed"


def helm_check(args):
    a = [x for x in args if not x.startswith("-")]
    if not a:
        return "helm needs a subcommand"
    if a[0] == "get":
        return (
            "helm get may print secret values"
            if a[1:2] in (["values"], ["all"])
            else None
        )
    return (
        None
        if a[0]
        in (
            "list",
            "ls",
            "status",
            "history",
            "version",
            "show",
            "search",
            "template",
            "lint",
        )
        else f"helm {a[0]} is not allowed"
    )


def doppler_check(args):
    a = [x for x in args if not x.startswith("-")]
    if a[:1] in (["projects"], ["configs"], ["environments"]) and a[1:] in (
        [],
        ["get"],
    ):
        return None
    # secret VALUES may be read (Claude pulls device and MCP API keys to read configs); never written or run
    if a[:1] == ["secrets"] and (
        a[1:2] in ([], ["get"], ["download"], ["names"]) or "--only-names" in args
    ):
        return None
    return "doppler may only read: projects, configs, secrets get/download/names (no set, delete, upload or run)"


def nix_check(args):
    a = [x for x in args if not x.startswith("-")]
    if a[:1] in (
        ["eval"],
        ["log"],
        ["why-depends"],
        ["path-info"],
        ["search"],
        ["derivation"],
    ):
        return None
    return (
        None
        if a[:2] in (["flake", "show"], ["flake", "metadata"], ["flake", "check"])
        else "nix may only eval, search or inspect"
    )


def only(*subs, what="inspect"):
    ok = [[s] for s in subs]

    def check(args):
        a = [x for x in args if not x.startswith("-")]
        return None if a[:1] in ok else f"may only {what}: {', '.join(subs)}"

    return check


def docker_check(args):
    a = [x for x in args if not x.startswith("-")]
    if a[:1] in [
        [s]
        for s in (
            "ps",
            "logs",
            "inspect",
            "images",
            "info",
            "version",
            "stats",
            "top",
            "port",
            "diff",
            "history",
        )
    ]:
        return None
    if a[:1] in (
        [c] for c in ("compose", "container", "image", "network", "volume")
    ) and a[1:2] in (["ps"], ["logs"], ["ls"], ["inspect"], ["config"], ["top"]):
        return None
    return "docker may only inspect"


def ansible_inventory_check(args):
    return (
        None
        if any(x in args for x in ("--list", "--graph", "--host"))
        else "ansible-inventory may only list"
    )


def jq_check(args):
    return no_flags("--rawfile", "--slurpfile")(args)


def man_check(args):
    return no_flags(
        "-P", "--pager", "-H", "--html", "-l", "--local-file", "-C", "-M", "-m"
    )(args)


def python_check(args):
    return (
        None
        if args[:2] == ["-m", "json.tool"]
        else "python3 may only run -m json.tool (no scripts)"
    )


def ssh_check(args):
    """ssh only with a remote command, and that command must itself pass every rule here."""
    with_arg = {"-i", "-o", "-p", "-l", "-F", "-J", "-b", "-c", "-E", "-S"}
    i = 0
    while i < len(args) and args[i].startswith("-"):
        if args[i] in (
            "-L",
            "-R",
            "-D",
            "-W",
            "-w",
            "-O",
            "-M",
            "-f",
            "-N",
            "-X",
            "-Y",
            "-A",
        ):
            return f"ssh {args[i]} is not allowed"
        if (
            args[i] == "-o"
            and i + 1 < len(args)
            and re.match(
                r"(?i)(ProxyCommand|LocalCommand|PermitLocalCommand|RemoteForward|LocalForward|DynamicForward)",
                args[i + 1],
            )
        ):
            return "that ssh option is not allowed"
        i += 2 if args[i] in with_arg else 1
    if i >= len(args):
        return "ssh needs a host"
    cmd = args[i + 1 :]
    if not cmd:
        return "interactive ssh is not allowed; give a read-only command"
    why = check_shell(" ".join(cmd))
    return None if why is None else f"remote command: {why}"


# AWS is read through the CLI with a read-only SSO profile: a `*-ro` profile whose role is in AINFO_AWS_RO_ROLES (every
# `*-ro` profile in ~/.aws/config maps to OpsReadOnly), so IAM refuses a write even if a rule here is wrong. On top of
# that: only read operations, nothing that hands out credentials or secret values, no file:// arguments.
AWS_RO_ROLES = {
    r.strip()
    for r in os.environ.get("AINFO_AWS_RO_ROLES", "OpsReadOnly").split(",")
    if r.strip()
}
AWS_VALUE_GLOBALS = {"--profile", "--region", "--output", "--query", "--color", "--cli-read-timeout",
                     "--cli-connect-timeout", "--cli-binary-format", "--max-items", "--page-size", "--starting-token"}  # fmt: skip
AWS_BAD_GLOBALS = {"--debug", "--endpoint-url", "--no-verify-ssl", "--ca-bundle", "--cli-auto-prompt"}  # fmt: skip
AWS_READ_PREFIXES = ("describe-", "get-", "list-", "lookup-", "search-", "batch-describe-", "batch-get-")
AWS_READ_OPS = {"filter-log-events", "head-bucket", "head-object", "simulate-principal-policy", "simulate-custom-policy"}  # fmt: skip
# read operations that return credentials, secret values or table data, or write an output file
AWS_DENY_OPS = {
    "secretsmanager": {"get-secret-value", "batch-get-secret-value"},
    "sts": {"get-session-token", "get-federation-token"},
    "ecr": {"get-login-password", "get-authorization-token"},
    "ecr-public": {"get-login-password", "get-authorization-token"},
    "codeartifact": {"get-authorization-token"},
    "eks": {"get-token"},
    "redshift": {"get-cluster-credentials", "get-cluster-credentials-with-iam"},
    "redshift-serverless": {"get-credentials"},
    "cognito-identity": {"get-credentials-for-identity", "get-open-id-token", "get-open-id-token-for-developer-identity"},
    "ec2": {"get-password-data"},
    "lightsail": {"get-instance-access-details", "get-relational-database-master-user-password"},
    "s3api": {"get-object", "get-object-torrent"},
    "dynamodb": {"get-item", "batch-get-item"},
}  # fmt: skip
AWS_DENY_FLAGS = {"--with-decryption", "--include-value", "--include-values"}


def aws_config():
    cp = configparser.RawConfigParser()
    try:
        cp.read(
            os.path.expanduser(os.environ.get("AWS_CONFIG_FILE") or "~/.aws/config")
        )
    except configparser.Error:
        pass
    return cp


def aws_profile_check(profile, cp):
    """None when the profile only reads: named *-ro and its role is a known read-only role."""
    if not profile.endswith("-ro"):
        return f"profile {profile} is not a -ro profile"
    sec = f"profile {profile}"
    if not cp.has_section(sec):
        return f"profile {profile} is not in ~/.aws/config"
    role = cp.get(sec, "sso_role_name", fallback="") or cp.get(
        sec, "role_arn", fallback=""
    ).rsplit("/", 1)[-1]
    if role not in AWS_RO_ROLES:
        return f"profile {profile} uses role {role or '(none)'}, not a read-only role ({', '.join(sorted(AWS_RO_ROLES))})"
    return None


def aws_ro_profiles(cp):
    names = [s[len("profile ") :] for s in cp.sections() if s.startswith("profile ")]
    return sorted(p for p in names if aws_profile_check(p, cp) is None)


def aws_check(args):
    pos, flags, profile, i = [], [], "", 0
    while i < len(args):
        a = args[i]
        if "file://" in a or "fileb://" in a:
            return "aws file:// arguments are not allowed"
        if a.startswith("--"):
            name, eq, val = a.partition("=")
            if name in AWS_BAD_GLOBALS:
                return f"aws {name} is not allowed"
            flags.append(name)
            if name in AWS_VALUE_GLOBALS and not eq:
                val = args[i + 1] if i + 1 < len(args) else ""
                i += 1
            if name == "--profile":
                profile = val
        elif len(pos) < 2:
            pos.append(a)
        i += 1
    if len(pos) < 2:
        return "aws needs a service and an operation"
    svc, op = pos[0], pos[1]
    if svc == "configure":
        return (
            None if op in ("list", "list-profiles") else "aws configure may only list"
        )
    cp = aws_config()
    ro = " ".join(aws_ro_profiles(cp)) or "(none found)"
    if svc in ("sso", "sso-oidc", "login", "logout"):
        # The login only refreshes the SSO token (the user approves it in the browser); every later call still needs
        # a -ro profile. Any other flag (--no-browser, --sso-session, ...) is denied.
        if svc != "sso" or op != "login" or set(flags) != {"--profile"}:
            return "aws: only `aws sso login --profile <name>-ro` is allowed"
        why = aws_profile_check(profile, cp)
        return f"{why}; read-only profiles: {ro}" if why else None
    if not profile:
        return f"aws needs --profile <name>-ro; read-only profiles: {ro}"
    why = aws_profile_check(profile, cp)
    if why:
        return f"{why}; read-only profiles: {ro}"
    if svc == "s3":
        return None if op == "ls" else "aws s3 may only ls"
    if op in AWS_DENY_OPS.get(svc, set()):
        return f"aws {svc} {op} returns credentials, secret values or data"
    bad = next((f for f in flags if f in AWS_DENY_FLAGS), None)
    if bad:
        return f"aws {bad} reveals secret values"
    if (
        svc == "glue"
        and op in ("get-connection", "get-connections")
        and "--hide-password" not in flags
    ):
        return "aws glue connections need --hide-password"
    if op.startswith(AWS_READ_PREFIXES) or op in AWS_READ_OPS:
        return None
    return f"aws {svc} {op} is not a read operation (describe-, get-, list-, lookup-, search-)"


READ_ONLY_WORDS = {
    **{
        w: None
        for w in [
            "ls",
            "cat",
            "head",
            "wc",
            "cut",
            "uniq",
            "tr",
            "grep",
            "egrep",
            "fgrep",
            "diff",
            "cmp",
            "column",
            "fold",
            "nl",
            "rev",
            "tac",
            "paste",
            "comm",
            "join",
            "xxd",
            "od",
            "strings",
            "file",
            "stat",
            "du",
            "df",
            "pwd",
            "basename",
            "dirname",
            "realpath",
            "readlink",
            "which",
            "type",
            "whoami",
            "id",
            "uname",
            "hostname",
            "date",
            "uptime",
            "free",
            "ps",
            "pgrep",
            "lsof",
            "echo",
            "printf",
            "true",
            "test",
            "[",
            "cd",
            "base64",
            "shasum",
            "sha256sum",
            "md5",
            "md5sum",
            "dig",
            "nslookup",
            "host",
        ]
    },
    "tail": no_flags("-f", "-F", "--follow"),
    "sort": no_flags("-o", "--output"),
    "rg": no_flags("--pre"),
    "fd": no_flags("-x", "--exec", "-X", "--exec-batch"),
    "ping": no_flags("-f"),
    "tailscale": only("status", "ip", "version", "netcheck"),
    "journalctl": no_flags("--vacuum-size", "--vacuum-time", "--rotate", "--flush"),
    "zfs": only("list", "get"),
    "zpool": only("list", "status", "get", "iostat"),
    "systemctl": only(
        "status",
        "list-units",
        "list-unit-files",
        "is-active",
        "is-enabled",
        "show",
        "cat",
        "list-timers",
    ),
    "launchctl": only("list", "print", "print-disabled", "blame"),
    "sed": sed_check,
    "awk": awk_check,
    "find": find_check,
    "jq": jq_check,
    "curl": curl_check,
    "git": git_check,
    "gh": gh_check,
    "aws": aws_check,
    "terraform": terraform_check,
    "tofu": terraform_check,
    "kubectl": kubectl_check,
    "helm": helm_check,
    "doppler": doppler_check,
    "nix": nix_check,
    "docker": docker_check,
    "ansible-inventory": ansible_inventory_check,
    "man": man_check,
    "ssh": ssh_check,
    "python3": python_check,
    "python": python_check,
}
FILE_READERS = {
    "cat",
    "head",
    "tail",
    "grep",
    "rg",
    "sed",
    "awk",
    "jq",
    "strings",
    "xxd",
    "od",
    "base64",
    "diff",
    "file",
    "stat",
    "ls",
    "find",
    "fd",
    "wc",
    "cut",
    "sort",
}
CONNECTORS = {"|", "&&", "||", ";"}
KEYWORDS = {
    "if",
    "for",
    "while",
    "until",
    "case",
    "function",
    "then",
    "do",
    "done",
    "fi",
    "{",
    "}",
}


def check_shell(cmd):
    """None when every command in the line only reads, else the reason."""
    if "\n" in cmd.strip():
        return "one command per call: no newlines"
    if "`" in cmd or "$(" in cmd or "<(" in cmd or ">(" in cmd:
        return "command substitution is not allowed"
    try:
        lex = shlex.shlex(cmd, posix=True, punctuation_chars=True)
        lex.whitespace_split = True
        toks = list(lex)
    except ValueError as e:
        return f"cannot parse the command ({e})"
    segs, cur, i = [], [], 0
    while i < len(toks):
        t, nxt = toks[i], (toks[i + 1] if i + 1 < len(toks) else "")
        if t in CONNECTORS:
            segs.append(cur)
            cur = []
        elif t in (">", ">>"):
            if nxt != "/dev/null":
                return "writing output to a file is not allowed (only /dev/null)"
            if cur and cur[-1] in ("1", "2"):
                cur.pop()  # the fd number of `2>/dev/null`
            i += 1
        elif t == ">&":
            if nxt not in ("1", "2"):
                return "that redirect is not allowed"
            if cur and cur[-1] in ("1", "2"):
                cur.pop()
            i += 1
        elif t and set(t) <= set("<>&;|()"):
            return f"shell operator {t!r} is not allowed"
        else:
            cur.append(t)
        i += 1
    segs.append(cur)
    for seg in segs:
        if not seg:
            return "empty command in a pipeline"
        word, args = seg[0], seg[1:]
        if re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", word):
            return "environment assignments before a command are not allowed"
        if word in KEYWORDS:
            return "shell loops and conditionals are not allowed; make separate calls"
        base = os.path.basename(word)
        if base not in READ_ONLY_WORDS:
            return f"{base} is not on the read-only list"
        check = READ_ONLY_WORDS[base]
        why = check(args) if check else None
        if why:
            return why
        if base in FILE_READERS:
            for a in args:
                if not a.startswith("-") and secret_path(a):
                    return f"{a} looks like a credential file"
    return None


# ---- MCP tools --------------------------------------------------------------------------------------------------
def words(name):
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", name)
    return [w for w in re.split(r"[_\-\s]+", s.lower()) if w]


READ_WORDS = {"get", "list", "read", "search", "query", "find", "describe", "show", "resolve", "fetch", "view", "retrieve", "status", "check", "validate", "diff", "logs", "log", "metrics", "export", "stats", "info", "details", "lookup", "explain", "inspect", "count", "analyze", "summary", "report", "usage", "guides", "sequentialthinking", "inheritable", "inherits", "names", "whoami", "me", "dependents", "dependencies", "impact", "symbol", "source", "structure", "hotspots", "routes", "imports", "classes", "functions", "wait", "stdout", "events", "playbooks", "roles", "doctor", "audit", "expand", "cached", "context", "policies", "rules", "architecture", "entities", "graph", "nodes", "relations", "ts", "changes"}  # fmt: skip
WRITE_WORDS = {"create", "update", "delete", "set", "add", "remove", "post", "send", "write", "edit", "run", "launch", "execute", "apply", "push", "merge", "approve", "suggest", "attach", "detach", "assign", "unassign", "change", "enable", "disable", "reset", "reboot", "rebuild", "resize", "power", "shutdown", "import", "rollback", "revoke", "lease", "lock", "unlock", "clone", "cancel", "toggle", "flush", "move", "insert", "replace", "register", "unregister", "authenticate", "complete", "upgrade", "purge", "install", "retry", "request", "confirm", "rename", "format", "generate", "index", "checkpoint", "commit", "reconfigure", "revert", "savepoint", "start", "stop", "restart", "kill", "sync", "mkdir", "save", "store", "observations", "predict", "trigger", "invoke", "optimize"}  # fmt: skip
# decisions the word rules would get wrong
MCP_ALLOW = {
    "mcp__doppler__secrets_download",
    "mcp__awx__awx_job_stdout", "mcp__awx__awx_job_events", "mcp__awx__awx_job_failure_summary", "mcp__awx__awx_system_info",
    "mcp__awx__project_playbooks", "mcp__awx__validate_playbook", "mcp__hetzner__hetzner_wait_for_action",
    "mcp__hetzner__hetzner_export_zonefile", "mcp__sequential-thinking__sequentialthinking", "mcp__memory__read_graph",
    "mcp__memory__search_nodes", "mcp__memory__open_nodes", "mcp__context-mode__ctx_search", "mcp__context-mode__ctx_stats",
    "mcp__context-mode__ctx_doctor", "mcp__token-savior__find_hotspots", "mcp__token-savior__discover_project_actions",
    "mcp__token-savior__detect_breaking_changes", "mcp__token-savior__build_commit_summary", "mcp__token-savior__ts_search",
    "mcp__mcp-stack-fullhavoc__verbosity_report", "mcp__mcp-stack-fullhavoc__validate_command",
    "mcp__token-optimizer-mcp__smart_read", "mcp__token-optimizer-mcp__smart_grep", "mcp__token-optimizer-mcp__smart_glob",
    "mcp__token-optimizer-mcp__get_cached", "mcp__token-optimizer-mcp__expand", "mcp__token-optimizer-mcp__wiki_query",
    "mcp__token-optimizer-mcp__wiki_read",
}  # fmt: skip
MCP_DENY = {
    # runs code, or writes through a back door
    "mcp__token-savior__ts_execute", "mcp__token-savior__run_project_action", "mcp__token-savior__run_impacted_tests",
    "mcp__context-mode__ctx_execute", "mcp__context-mode__ctx_execute_file", "mcp__context-mode__ctx_batch_execute",
    "mcp__context-mode__ctx_index", "mcp__context-mode__ctx_fetch_and_index", "mcp__awx__ansible_playbook",
    "mcp__awx__ansible_task", "mcp__awx__ansible_role", "mcp__awx__ansible_inventory", "mcp__hetzner__hetzner_request_console",
    "mcp__token-optimizer-mcp__optimize_session", "mcp__token-optimizer-mcp__wiki_write",
}  # fmt: skip
# `<module>_manage` tools (OPNsense) take a camelCase `method` such as aliasGetItem or filterAddRule
MANAGE_WRITE = {"add", "del", "delete", "set", "toggle", "apply", "revert", "import", "reconfigure", "flush", "move", "update", "savepoint", "cancel", "start", "stop", "restart", "reboot", "kill", "create", "install", "upgrade", "reset", "run", "exec", "reload", "sync", "upload", "download", "rollback", "enable", "disable", "poweroff", "halt", "remove", "renew", "revoke", "save", "write", "send", "test", "provision", "migrate", "restore", "backup", "clean", "clear", "mark", "rotate", "generate", "register", "sign"}  # fmt: skip
MANAGE_READ = {
    "get",
    "list",
    "search",
    "find",
    "stats",
    "status",
    "info",
    "show",
    "query",
    "dump",
    "log",
    "logs",
    "count",
    "check",
    "view",
    "read",
    "version",
    "detail",
    "details",
    "top",
    "summary",
    "names",
    "options",
}


def mcp_decision(tool, tin):
    """None when the MCP tool only reads, else the reason."""
    if tool in MCP_ALLOW:
        return None
    if tool in MCP_DENY:
        return "that MCP tool can change something, run code or reveal a secret value"
    parts = tool.split("__", 2)
    name = parts[2] if len(parts) == 3 else tool
    if name.endswith("_manage"):
        method = str((tin or {}).get("method") or "")
        mw = words(method)
        if not mw:
            return "a _manage tool needs a read-only method"
        if any(w in MANAGE_WRITE for w in mw):
            return f"method {method} changes something"
        return (
            None
            if any(w in MANAGE_READ for w in mw)
            else f"method {method} is not known to be read-only"
        )
    nw = words(name)
    if any(w in WRITE_WORDS for w in nw):
        return "that MCP tool name says it changes something"
    return (
        None
        if any(w in READ_WORDS for w in nw)
        else "that MCP tool is not known to be read-only"
    )


# ---- decision ---------------------------------------------------------------------------------------------------
def decide(ev):
    """(allow, reason)"""
    tool, tin = ev.get("tool_name", ""), ev.get("tool_input") or {}
    if tool in BUILTIN_ALLOW:
        for k in PATH_TOOLS.get(tool, ()):
            if tin.get(k) and secret_path(tin[k]):
                return (
                    False,
                    f"{tin[k]} looks like a credential file; ask the user for what you need from it",
                )
        return True, ""
    if tool == "Bash":
        why = check_shell(str(tin.get("command") or ""))
        return (why is None), (why or "")
    if tool.startswith("mcp__"):
        why = mcp_decision(tool, tin)
        return (why is None), (why or "")
    return (
        False,
        f"{tool} is not allowed: ainfo is read-only and online research belongs to Lumo",
    )


def main():
    try:
        ev = json.load(sys.stdin)
    except ValueError:
        ev = {}
    allow, reason = decide(ev)
    msg = (
        "ainfo read-only guard: allowed"
        if allow
        else f"ainfo is read-only: {reason}. Do not retry; report what you could not check."
    )
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "allow" if allow else "deny",
                    "permissionDecisionReason": msg,
                }
            }
        )
    )


if __name__ == "__main__":
    main()
