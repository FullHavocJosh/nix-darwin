import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import aifo_guard as g


def bash(cmd):
    return g.decide({"tool_name": "Bash", "tool_input": {"command": cmd}})[0]


def mcp(tool, **tin):
    return g.decide({"tool_name": tool, "tool_input": tin})[0]


class Bash(unittest.TestCase):
    def test_reads_allowed(self):
        for c in (
            "ls -la /tmp",
            "git status --short",
            "git -C /Users/havoc/nix-darwin log --oneline -5",
            "git diff HEAD~1 -- foo.py",
            "git branch -a",
            "git grep -n foo",
            "git show abc123:path/file",
            "gh pr view 12 --json title",
            "gh pr list --state all",
            "gh api repos/x/y/pulls/1/comments",
            "gh api -X GET repos/x/y",
            "terraform validate",
            "terraform state list",
            "terraform fmt -check",
            "kubectl get pods -A",
            "kubectl logs deploy/foo --tail=50",
            "helm list -A",
            "grep -rn foo . | head -20",
            "cat README.md | wc -l",
            "sed -n '1,20p' file.py",
            "jq -r '.a' x.json",
            "find . -name '*.tf' -type f",
            "curl -s http://192.168.144.1/api/core/firmware/status",
            "curl -sk -H 'Authorization: Bearer x' https://host/api",
            "ssh root@azerothcore.rollet.family 'docker ps'",
            "ssh -i ~/.ssh/k root@host 'journalctl -u foo -n 50 | tail'",
            "ls /nope 2>/dev/null",
            "git log 2>&1 | head",
            "cd /tmp && ls",
            "doppler secrets --only-names --project p --config c",
            "man grep",
            "zpool status",
            "nix eval .#foo",
            "date",
        ):
            self.assertTrue(bash(c), c)

    def test_writes_denied(self):
        for c in (
            "rm -rf x",
            "echo hi > file.txt",
            "echo hi >> file.txt",
            "cat a | tee b",
            "sed -i 's/a/b/' f",
            "sed -i.bak 's/a/b/' f",
            "sed 's/a/b/w out.txt' f",
            "find . -delete",
            "find . -exec rm {} ;",
            "awk '{print > \"x\"}' f",
            "curl -X POST http://x",
            "curl -d a=b http://x",
            "curl -o out http://x",
            "curl -T f http://x",
            "git commit -m x",
            "git push",
            "git checkout -b x",
            "git branch -D x",
            "git branch newname",
            "git stash",
            "git reset --hard",
            "git diff --output=x",
            "gh pr create",
            "gh pr comment 1 -b hi",
            "gh pr merge 1",
            "gh api -X POST repos/x/y",
            "gh api repos/x/y -f a=b",
            "terraform apply",
            "terraform plan",
            "terraform destroy",
            "terraform state rm x",
            "kubectl apply -f x",
            "kubectl delete pod x",
            "kubectl get secret foo -o yaml",
            "kubectl exec -it x -- sh",
            "helm install a b",
            "helm get values x",
            "ssh root@host",
            "ssh root@host 'rm -rf /'",
            "ssh -L 80:localhost:80 host 'ls'",
            "scp a b:",
            "doppler secrets get X --plain",
            "doppler run -- env",
            'python3 -c \'open("f","w")\'',
            "python3 script.py",
            "env",
            "printenv",
            "sudo ls",
            "bash -c 'ls'",
            "xargs rm",
            "ls; rm x",
            "ls && rm x",
            "ls | xargs rm",
            "echo $(rm x)",
            "echo `rm x`",
            "FOO=1 ls",
            "for i in 1 2; do ls; done",
            "ls &",
            "cat < file",
            "cat <<EOF\nx\nEOF",
            "tail -f x",
            "sort -o out in",
            "cat ~/.ssh/id_ed25519",
            "cat .env",
            "grep x terraform.tfvars",
            "mv a b",
            "cp a b",
            "touch x",
            "mkdir x",
            "launchctl unload x",
            "systemctl restart x",
            "docker run x",
            "docker exec x sh",
        ):
            self.assertFalse(bash(c), c)


class Tools(unittest.TestCase):
    def test_builtins(self):
        for t in (
            "Edit",
            "Write",
            "MultiEdit",
            "NotebookEdit",
            "WebFetch",
            "WebSearch",
            "Agent",
            "Task",
            "Skill",
            "Foo",
        ):
            self.assertFalse(g.decide({"tool_name": t, "tool_input": {}})[0], t)
        self.assertTrue(
            g.decide({"tool_name": "Read", "tool_input": {"file_path": "/a/b.py"}})[0]
        )
        self.assertFalse(
            g.decide({"tool_name": "Read", "tool_input": {"file_path": "/a/.env"}})[0]
        )
        self.assertFalse(
            g.decide(
                {"tool_name": "Read", "tool_input": {"file_path": "/h/.ssh/id_rsa"}}
            )[0]
        )
        self.assertTrue(
            g.decide(
                {"tool_name": "Grep", "tool_input": {"pattern": ".env", "path": "/a"}}
            )[0]
        )
        self.assertTrue(
            g.decide({"tool_name": "ToolSearch", "tool_input": {"query": "x"}})[0]
        )

    def test_mcp_reads(self):
        for t in (
            "mcp__github__github_file_get",
            "mcp__github__github_pr_comments_get",
            "mcp__github__github_pr_details",
            "mcp__github__github_pr_changes",
            "mcp__github__github_issues_list",
            "mcp__github__github_repos_list",
            "mcp__hetzner__hetzner_get_server",
            "mcp__hetzner__hetzner_list_servers",
            "mcp__hetzner__hetzner_wait_for_action",
            "mcp__hetzner__hetzner_export_zonefile",
            "mcp__terraform__providerDetails",
            "mcp__terraform__resourceArgumentDetails",
            "mcp__terraform__moduleSearch",
            "mcp__terraform__providerGuides",
            "mcp__context7__query-docs",
            "mcp__context7__resolve-library-id",
            "mcp__truenas__list_pools",
            "mcp__truenas__get_dataset",
            "mcp__awx__awx_job_stdout",
            "mcp__awx__awx_jobs_list",
            "mcp__awx__list_playbooks",
            "mcp__doppler__secrets_names",
            "mcp__doppler__projects_list",
            "mcp__token-savior__find_symbol",
            "mcp__token-savior__get_function_source",
            "mcp__token-savior__search_codebase",
            "mcp__token-optimizer-mcp__smart_read",
            "mcp__mcp-stack-fullhavoc__read_context_file",
            "mcp__mcp-stack-fullhavoc__get_infrastructure_context",
            "mcp__memory__search_nodes",
            "mcp__sequential-thinking__sequentialthinking",
            "mcp__atlassian__getJiraIssue",
            "mcp__atlassian__searchJiraIssuesUsingJql",
            "mcp__atlassian__getConfluencePage",
        ):
            self.assertTrue(mcp(t), t)

    def test_mcp_writes(self):
        for t in (
            "mcp__github__github_pr_create",
            "mcp__github__github_pr_approve",
            "mcp__github__github_pr_suggest_change",
            "mcp__hetzner__hetzner_create_server",
            "mcp__hetzner__hetzner_delete_server",
            "mcp__hetzner__hetzner_power_off",
            "mcp__hetzner__hetzner_reboot",
            "mcp__hetzner__hetzner_request_console",
            "mcp__hetzner__hetzner_reset_server_password",
            "mcp__hetzner__hetzner_set_firewall_rules",
            "mcp__doppler__secrets_update",
            "mcp__doppler__secrets_get",
            "mcp__doppler__secrets_download",
            "mcp__doppler__secrets_list",
            "mcp__doppler__configs_lock",
            "mcp__truenas__delete_dataset",
            "mcp__truenas__rollback_snapshot",
            "mcp__truenas__create_snapshot",
            "mcp__awx__awx_job_launch",
            "mcp__awx__ansible_playbook",
            "mcp__awx__ansible_task",
            "mcp__awx__git_push_project",
            "mcp__memory__create_entities",
            "mcp__memory__delete_entities",
            "mcp__prettier__format-files",
            "mcp__token-savior__replace_symbol_source",
            "mcp__token-savior__ts_execute",
            "mcp__token-optimizer-mcp__smart_edit",
            "mcp__token-optimizer-mcp__smart_write",
            "mcp__context-mode__ctx_execute",
            "mcp__plugin_engineering_slack__authenticate",
            "mcp__mcp-server-chart__generate_pie_chart",
            "mcp__unknown__frobnicate",
        ):
            self.assertFalse(mcp(t), t)

    def test_manage(self):
        self.assertTrue(mcp("mcp__opnsense__firewall_manage", method="aliasGetItem"))
        self.assertTrue(mcp("mcp__opnsense__firewall_manage", method="filterGetRule"))
        self.assertTrue(
            mcp("mcp__opnsense__firewall_manage", method="aliasUtilFindReferences")
        )
        self.assertTrue(
            mcp("mcp__opnsense__diagnostics_manage", method="systemGetStatus")
        )
        for m in (
            "aliasAddItem",
            "filterDelRule",
            "filterBaseApply",
            "aliasUtilUpdateBogons",
            "aliasSet",
            "filterToggleRule",
            "foo",
            "",
        ):
            self.assertFalse(mcp("mcp__opnsense__firewall_manage", method=m), m)
        self.assertFalse(mcp("mcp__opnsense__firewall_manage"))


if __name__ == "__main__":
    unittest.main()
