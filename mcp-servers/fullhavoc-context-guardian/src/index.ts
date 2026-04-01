#!/usr/bin/env node
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
  ListResourcesRequestSchema,
  ReadResourceRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import * as fs from "fs/promises";
import * as path from "path";
import { fileURLToPath } from "url";
import os from "os";
import { exec } from "child_process";
import { promisify } from "util";

const execAsync = promisify(exec);

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Expand ~ to home directory
function expandHome(filepath: string): string {
  if (filepath.startsWith("~/")) {
    return path.join(os.homedir(), filepath.slice(2));
  }
  return filepath;
}

// Load infrastructure context
async function loadInfrastructureContext() {
  try {
    const contextPath = path.join(
      __dirname,
      "..",
      "infrastructure-context.json",
    );
    const data = await fs.readFile(contextPath, "utf-8");
    return JSON.parse(data);
  } catch (error) {
    console.error("Error loading infrastructure context:", error);
    return null;
  }
}

// Read file from context paths
async function readContextFile(filepath: string): Promise<string> {
  try {
    const expandedPath = expandHome(filepath);
    const data = await fs.readFile(expandedPath, "utf-8");
    return data;
  } catch (error: any) {
    throw new Error(`Failed to read ${filepath}: ${error.message}`);
  }
}

// List files in context directories recursively
async function listContextFiles(dirPath: string): Promise<string[]> {
  const results: string[] = [];

  async function walk(currentPath: string, basePath: string) {
    try {
      const expandedPath = expandHome(currentPath);
      const entries = await fs.readdir(expandedPath, { withFileTypes: true });

      for (const entry of entries) {
        const fullPath = path.join(currentPath, entry.name);

        if (entry.isDirectory()) {
          await walk(fullPath, basePath);
        } else if (entry.isFile() && entry.name.endsWith(".md")) {
          results.push(fullPath);
        }
      }
    } catch (error) {
      // Silently skip directories we can't read
    }
  }

  await walk(dirPath, dirPath);
  return results;
}

const READ_ONLY_PROFILES = [
  "ps-prod-ro",
  "ps-dev-ro",
  "tm-prod-ro",
  "tm-dev-ro",
  "lb-prod-ro",
  "lb-dev-ro",
  "int-prod-ro",
] as const;

type ReadOnlyProfile = (typeof READ_ONLY_PROFILES)[number];

async function awsSsoLogin(profile: ReadOnlyProfile): Promise<string> {
  const { stdout, stderr } = await execAsync(
    `aws sso login --profile ${profile}`,
    {
      timeout: 120000,
    },
  );
  return stdout || stderr || `SSO login initiated for profile: ${profile}`;
}

const server = new Server(
  {
    name: "fullhavoc-context-guardian",
    version: "1.0.0",
  },
  {
    capabilities: {
      tools: {},
      resources: {},
    },
  },
);

// List available tools
server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: [
      {
        name: "get_infrastructure_context",
        description:
          "Get full infrastructure context including network architecture, components, and critical principles",
        inputSchema: {
          type: "object",
          properties: {},
        },
      },
      {
        name: "get_network_architecture",
        description:
          "Get network architecture details (OPNsense vs K8s nginx separation of concerns)",
        inputSchema: {
          type: "object",
          properties: {},
        },
      },
      {
        name: "read_context_file",
        description:
          "Read a documentation file from aicontexts or home-infrastructure directories",
        inputSchema: {
          type: "object",
          properties: {
            filepath: {
              type: "string",
              description: "Path to the file (supports ~ for home directory)",
            },
          },
          required: ["filepath"],
        },
      },
      {
        name: "list_context_files",
        description:
          "List available markdown documentation files in a context directory (recursive)",
        inputSchema: {
          type: "object",
          properties: {
            directory: {
              type: "string",
              description:
                "Directory to list (e.g., ~/aicontexts, ~/home-infrastructure)",
            },
          },
          required: ["directory"],
        },
      },
      {
        name: "aws_sso_login",
        description:
          "Trigger AWS SSO login for a read-only AWS profile. Use this before running AWS CLI commands that require authentication. Available profiles: ps-prod-ro, ps-dev-ro, tm-prod-ro, tm-dev-ro, lb-prod-ro, lb-dev-ro, int-prod-ro",
        inputSchema: {
          type: "object",
          properties: {
            profile: {
              type: "string",
              enum: [...READ_ONLY_PROFILES],
              description:
                "The read-only AWS profile to authenticate. Must be one of: ps-prod-ro, ps-dev-ro, tm-prod-ro, tm-dev-ro, lb-prod-ro, lb-dev-ro, int-prod-ro",
            },
          },
          required: ["profile"],
        },
      },
    ],
  };
});

// Handle tool calls
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  try {
    switch (name) {
      case "get_infrastructure_context": {
        const context = await loadInfrastructureContext();
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify(context, null, 2),
            },
          ],
        };
      }

      case "get_network_architecture": {
        const context = await loadInfrastructureContext();
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify(
                context?.architecture?.network || {},
                null,
                2,
              ),
            },
          ],
        };
      }

      case "read_context_file": {
        if (!args || typeof args !== "object" || !("filepath" in args)) {
          throw new Error("filepath argument is required");
        }
        const filepath = args.filepath as string;
        const content = await readContextFile(filepath);
        return {
          content: [
            {
              type: "text",
              text: content,
            },
          ],
        };
      }

      case "list_context_files": {
        if (!args || typeof args !== "object" || !("directory" in args)) {
          throw new Error("directory argument is required");
        }
        const directory = args.directory as string;
        const files = await listContextFiles(directory);
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify(files, null, 2),
            },
          ],
        };
      }

      case "aws_sso_login": {
        if (!args || typeof args !== "object" || !("profile" in args)) {
          throw new Error("profile argument is required");
        }
        const profile = args.profile as string;
        if (!READ_ONLY_PROFILES.includes(profile as ReadOnlyProfile)) {
          throw new Error(
            `Invalid profile: ${profile}. Must be one of: ${READ_ONLY_PROFILES.join(", ")}`,
          );
        }
        const result = await awsSsoLogin(profile as ReadOnlyProfile);
        return {
          content: [
            {
              type: "text",
              text: result,
            },
          ],
        };
      }

      default:
        throw new Error(`Unknown tool: ${name}`);
    }
  } catch (error: any) {
    return {
      content: [
        {
          type: "text",
          text: `Error: ${error.message}`,
        },
      ],
      isError: true,
    };
  }
});

// List resources
server.setRequestHandler(ListResourcesRequestSchema, async () => {
  const context = await loadInfrastructureContext();
  const resources: any[] = [];

  if (context) {
    resources.push({
      uri: "context://infrastructure",
      name: "Infrastructure Context",
      description: "Full infrastructure context and architecture",
      mimeType: "application/json",
    });

    resources.push({
      uri: "context://network-architecture",
      name: "Network Architecture",
      description: "Network architecture and nginx separation principles",
      mimeType: "application/json",
    });
  }

  return { resources };
});

// Read resources
server.setRequestHandler(ReadResourceRequestSchema, async (request) => {
  const { uri } = request.params;
  const context = await loadInfrastructureContext();

  switch (uri) {
    case "context://infrastructure":
      return {
        contents: [
          {
            uri,
            mimeType: "application/json",
            text: JSON.stringify(context, null, 2),
          },
        ],
      };

    case "context://network-architecture":
      return {
        contents: [
          {
            uri,
            mimeType: "application/json",
            text: JSON.stringify(context?.architecture?.network || {}, null, 2),
          },
        ],
      };

    default:
      throw new Error(`Unknown resource: ${uri}`);
  }
});

// Start the server
async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("fullhavoc-context-guardian MCP server running on stdio");
}

main().catch((error) => {
  console.error("Fatal error in main():", error);
  process.exit(1);
});
