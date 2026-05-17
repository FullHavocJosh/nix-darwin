/**
 * OpenCode Plugin: Model Filter
 *
 * Filters out non-Claude and non-free models from GitHub Copilot and OpenCode Zen providers.
 * This enforces the restriction to only show Claude models and designated free models.
 */

const ALLOWED_MODELS = {
  "github-copilot": [
    "claude-opus-4.7",
    "claude-opus-4.5",
    "claude-sonnet-4.6",
    "claude-sonnet-4.5",
    "claude-haiku-4.5",
  ],
  opencode: [
    // Claude models (paid)
    "claude-opus-4.7",
    "claude-opus-4.6",
    "claude-opus-4.5",
    "claude-opus-4.1",
    "claude-sonnet-4.6",
    "claude-sonnet-4.5",
    "claude-sonnet-4",
    "claude-haiku-4.5",
    "claude-3-5-haiku",
    // Free models
    "big-pickle",
    "deepseek-v4-flash-free",
    "minimax-m2.5-free",
    "nemotron-3-super-free",
  ],
};

module.exports = {
  name: "model-filter",
  version: "1.0.0",

  hooks: {
    "models:filter": async ({ models, provider }) => {
      const allowedForProvider = ALLOWED_MODELS[provider];

      if (!allowedForProvider) {
        // For providers not in the allowlist (llama.cpp, etc), allow all
        return models;
      }

      // Filter to only allowed models
      const filtered = models.filter((model) => {
        const modelId = model.id || model.name;
        return allowedForProvider.includes(modelId);
      });

      console.log(
        `[model-filter] Provider: ${provider}, Original: ${models.length}, Filtered: ${filtered.length}`,
      );

      return filtered;
    },
  },
};
