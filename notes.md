ToDo:
Impliment MCP Servers for use with Claude Code and Crush:
claude mcp add -s user context7 -- npx -y @upstash/context7-mcp
claude mcp add -s user aws-core-mcp-server --env FASTMCP_LOG_LEVEL=ERROR -- uvx awslabs.core-mcp-server@latest
claude mcp add -s user aws-documentation-mcp --env FASTMCP_LOG_LEVEL=ERROR --env AWS_DOCUMENTATION_PARTITION=aws -- uvx awslabs.aws-documentation-mcp-server@latest
claude mcp add -s user aws-eks-mcp-server --env FASTMCP_LOG_LEVEL=ERROR -- uvx awslabs.eks-mcp-server@latest
claude mcp add -s user aws-cost-analysis-mcp-server --env FASTMCP_LOG_LEVEL=ERROR --env AWS_PROFILE=services -- uvx awslabs.cost-analysis-mcp-server@latest
claude mcp add -s user aws-diagram-mcp-server --env FASTMCP_LOG_LEVEL=ERROR -- uvx awslabs.aws-diagram-mcp-server@latest
claude mcp add -s user aws-terraform-mcp --env FASTMCP_LOG_LEVEL=ERROR -- uvx awslabs.terraform-mcp-server@latest
claude mcp add -s user mcp-server-chart -- npx -y @antv/mcp-server-chart
claude mcp add -s user iterm-mcp -- npx -y iterm-mcp

