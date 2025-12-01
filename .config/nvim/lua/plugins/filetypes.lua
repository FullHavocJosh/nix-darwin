-- Additional filetype detection and configuration
return {
  {
    "LazyVim/LazyVim",
    opts = function()
      -- Extend filetype detection
      vim.filetype.add({
        extension = {
          -- Terraform
          tf = "terraform",
          tfvars = "terraform",
          tftest = "terraform",

          -- HCL
          hcl = "hcl",

          -- Jinja2 templates
          j2 = "jinja",
          jinja = "jinja",
          jinja2 = "jinja",

          -- PowerShell
          ps1 = "ps1",
          psm1 = "psm1",
          psd1 = "ps1",

          -- TCL (F5 BigIP iRules)
          tcl = "tcl",

          -- GLSL shaders
          glsl = "glsl",
          vert = "glsl",
          frag = "glsl",

          -- SQL
          sql = "sql",

          -- TOML
          toml = "toml",
        },
        filename = {
          -- Terraform
          ["terraform.tfvars"] = "terraform",
          [".terraform.lock.hcl"] = "hcl",
          [".tflint.hcl"] = "hcl",
          ["terragrunt.hcl"] = "hcl",

          -- Docker
          ["Dockerfile"] = "dockerfile",
          ["docker-compose.yml"] = "yaml.docker-compose",
          ["docker-compose.yaml"] = "yaml.docker-compose",
          ["compose.yml"] = "yaml.docker-compose",
          ["compose.yaml"] = "yaml.docker-compose",

          -- Ansible
          ["ansible.cfg"] = "dosini",
          [".ansible-lint"] = "yaml",
          [".yamllint"] = "yaml",

          -- Shell
          [".zshrc"] = "zsh",
          [".bashrc"] = "bash",
          [".bash_profile"] = "bash",
          [".zshenv"] = "zsh",

          -- Makefiles
          ["Makefile"] = "make",
          ["makefile"] = "make",

          -- Nix
          ["flake.lock"] = "json",
        },
        pattern = {
          -- Ansible playbooks and roles
          [".*/playbooks/.*%.ya?ml"] = "yaml.ansible",
          [".*/roles/.*/tasks/.*%.ya?ml"] = "yaml.ansible",
          [".*/roles/.*/handlers/.*%.ya?ml"] = "yaml.ansible",
          [".*/ansible/.*%.ya?ml"] = "yaml.ansible",
          [".*playbook.*%.ya?ml"] = "yaml.ansible",

          -- Kubernetes manifests
          [".*k8s.*%.ya?ml"] = "yaml.kubernetes",
          [".*/kubernetes/.*%.ya?ml"] = "yaml.kubernetes",

          -- GitHub Actions
          [".github/workflows/.*%.ya?ml"] = "yaml.github-actions",

          -- GitLab CI
          ["%.gitlab%-ci%.ya?ml"] = "yaml.gitlab-ci",

          -- Docker Compose
          ["docker%-compose.*%.ya?ml"] = "yaml.docker-compose",

          -- CloudFormation
          [".*cloudformation.*%.ya?ml"] = "yaml.cloudformation",

          -- Jinja templates
          [".*%.j2"] = "jinja",
          [".*%.jinja2?"] = "jinja",

          -- Shell scripts without extension
          [".*%.sh%.j2"] = "sh",
        },
      })
    end,
  },
}
