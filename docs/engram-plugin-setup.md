# Setting Up the Engram Plugin for Claude

This guide explains how to connect the **Engram staging environment** to Claude Desktop or Claude Code CLI on macOS.

> Engram staging is available only when Zscaler or the required VPN is connected.

## What is Engram?

Engram is a centralized memory system for AI coding agents. It saves durable facts and memories in one central location.

Engram organizes facts into three scopes:

- **User-level memories** — your stable preferences, working style, expertise, and recurring goals.
- **Repository-level memories** — architecture decisions, conventions, standard commands, testing practices, and other facts specific to a repository.
- **Organization-level memories** — shared Tata 1mg standards, processes, and cross-project knowledge.

You can view your user, repository, and organization memories in the [Engram dashboard](https://stag.deputydev.ai/engram).

The Engram plugin installs a local MCP server configuration and a set of Claude skills, including:

- `engram-remember` — saves a durable user, repository, or organization fact.
- `engram-extract` — extracts high-confidence facts from a current conversation, pasted transcript, or old Claude session.
- `engram-import-project` — reviews project instruction files and imports stable repository conventions.
- `engram-checkpoint` — reviews recent conversation context for facts worth preserving.
- `engram-status` — verifies authentication, MCP connectivity, and repository resolution.

## Prerequisites

Before continuing, ensure that:

- Zscaler or the required VPN is connected.
- Python is installed.
- Homebrew is installed.
- `uv`, the Python package manager used to run the local MCP integration, is installed.
- You have access to your Tata 1mg Gmail account.

### Install `uv`

Install `uv` with Homebrew:

```bash
brew install uv
```

Verify the installation:

```bash
uv --version
```

If the command returns a version number, `uv` is installed correctly.

---

# Claude Desktop Setup

## 1. Sign in to Engram

Open the [Engram staging dashboard](https://stag.deputydev.ai/engram) and sign in using your Tata 1mg Gmail account.

If login fails or you cannot authenticate, report the issue before continuing.

## 2. Generate a Personal Access Token

1. Open [Engram API Keys](https://stag.deputydev.ai/engram/api-keys).
2. Generate a new API key or Personal Access Token (PAT).
3. Copy the token immediately.

A token looks similar to:

```text
engpat_live_xxxxxxxxxxxxxxxxx
```

> Treat the PAT like a password. Do not commit it to Git, paste it into project files, include it in screenshots, or share it with anyone.

## 3. Configure the Environment Variable

Replace the example token in the commands below with your actual PAT. Use the section for your shell.

### Current Zsh or Bash Session

```bash
export ENGRAM_PERSONAL_ACCESS_TOKEN="engpat_live_xxxxxxxxxxxxxxxxx"
```

### Persist for Zsh

```bash
echo 'export ENGRAM_PERSONAL_ACCESS_TOKEN="engpat_live_xxxxxxxxxxxxxxxxx"' >> ~/.zshrc
source ~/.zshrc
```

### Persist for Bash

```bash
echo 'export ENGRAM_PERSONAL_ACCESS_TOKEN="engpat_live_xxxxxxxxxxxxxxxxx"' >> ~/.bashrc
source ~/.bashrc
```

### Persist for Fish

```fish
set -Ux ENGRAM_PERSONAL_ACCESS_TOKEN "engpat_live_xxxxxxxxxxxxxxxxx"
```

### Make the Token Available to macOS GUI Applications

Claude Desktop is a GUI application, so make the variable available through `launchctl`:

```bash
launchctl setenv ENGRAM_PERSONAL_ACCESS_TOKEN "engpat_live_xxxxxxxxxxxxxxxxx"
```

Verify that `launchctl` has the value:

```bash
launchctl getenv ENGRAM_PERSONAL_ACCESS_TOKEN
```

## 4. Restart Claude Desktop

Quit Claude Desktop completely:

```bash
osascript -e 'quit app "Claude"'
```

Launch it again:

```bash
open /Applications/Claude.app
```

Restarting Claude after running `launchctl setenv` ensures that it receives the latest environment variable.

## 5. Add the Engram Plugin Marketplace

In Claude Desktop:

1. Open **Settings**.
2. Go to **Plugins**.
3. Click **Add** in the top-right corner.
4. Select **Add Marketplace**.
5. Enter the repository URL:

   ```text
   https://github.com/vaibhavmeena1/engram_backend
   ```

6. Leave **Auto Sync** enabled.
7. Click **Sync**.
8. Wait for synchronization to complete successfully.

## 6. Enable the Plugin

1. Return to **Plugins**.
2. Open the **Personal** tab.
3. Locate `engram_plugin` and enable it.
4. Wait for the local MCP server confirmation dialog.
5. Approve the **This plugin includes local MCP servers** prompt.

## 7. Reload Claude Skills

Open Claude Code mode in Claude Desktop and run:

```text
/reload-skills
```

Wait for the reload to complete.

## 8. Verify Engram

Run:

```text
/engram:engram-status
```

A successful status response confirms that:

- the plugin is installed and enabled,
- the local MCP server is running,
- the Personal Access Token is available,
- the current repository can be resolved when applicable, and
- the Engram integration is functioning correctly.

---

# Claude Code CLI Setup

## 1. Sign in to Engram

Open the [Engram staging dashboard](https://stag.deputydev.ai/engram) and sign in using your Tata 1mg Gmail account.

If login fails or you cannot authenticate, report the issue before continuing.

## 2. Generate a Personal Access Token

1. Open [Engram API Keys](https://stag.deputydev.ai/engram/api-keys).
2. Generate a new API key or Personal Access Token.
3. Copy the token immediately.

A token looks similar to:

```text
engpat_live_xxxxxxxxxxxxxxxxx
```

> Treat the PAT like a password. Do not commit it to Git, paste it into project files, include it in screenshots, or share it with anyone.

## 3. Configure the Environment Variable

Claude Code runs inside your terminal, so the terminal must have access to the PAT. Replace the example value with your actual token and use the section for your shell.

### Current Zsh or Bash Session

```bash
export ENGRAM_PERSONAL_ACCESS_TOKEN="engpat_live_xxxxxxxxxxxxxxxxx"
```

### Persist for Zsh

```bash
echo 'export ENGRAM_PERSONAL_ACCESS_TOKEN="engpat_live_xxxxxxxxxxxxxxxxx"' >> ~/.zshrc
source ~/.zshrc
```

### Persist for Bash

```bash
echo 'export ENGRAM_PERSONAL_ACCESS_TOKEN="engpat_live_xxxxxxxxxxxxxxxxx"' >> ~/.bashrc
source ~/.bashrc
```

### Current Fish Session

```fish
set -gx ENGRAM_PERSONAL_ACCESS_TOKEN "engpat_live_xxxxxxxxxxxxxxxxx"
```

### Persist for Fish

```fish
set -Ux ENGRAM_PERSONAL_ACCESS_TOKEN "engpat_live_xxxxxxxxxxxxxxxxx"
```

Verify that the variable is available:

```bash
echo $ENGRAM_PERSONAL_ACCESS_TOKEN
```

The command should print your PAT. Do not share the output.

## 4. Launch Claude Code

Start Claude Code from the same terminal in which the environment variable is available:

```bash
claude
```

## 5. Add the Engram Plugin Marketplace

Inside Claude Code, run:

```text
/plugin marketplace add https://github.com/vaibhavmeena1/engram_backend
```

This adds the public Engram plugin marketplace to Claude Code.

## 6. Install the Engram Plugin

Run:

```text
/plugin install engram@engram-plugins
```

If prompted for the Engram Personal Access Token, paste the PAT generated earlier and continue. Enable the plugin if it is not enabled automatically.

## 7. Reload Claude Skills

Run:

```text
/reload-skills
```

Wait for the reload to complete successfully.

## 8. Verify Engram

Run:

```text
/engram:engram-status
```

A successful status response confirms that:

- the plugin is installed and enabled,
- the MCP server is running,
- the Personal Access Token is available,
- the current repository can be resolved when applicable, and
- the Engram integration is functioning correctly.

---

# Extract Memories from an Existing Session

Complete the Claude Desktop or Claude Code CLI setup and verify Engram before extracting memories.

## 1. Open the Existing Session

Open the Claude conversation whose durable facts you want to save:

- In Claude Desktop, select the conversation from your chat history.
- In Claude Code, resume the previous conversation from the session picker.
- If the original session cannot be reopened, start a new conversation and paste the relevant transcript into it.

Make sure the full conversation or relevant transcript is visible to Claude before continuing.

## 2. Run Engram Extract

Run:

```text
/engram:engram-extract
```

You can also include a direct instruction:

```text
/engram:engram-extract Extract and save the durable facts from this session.
```

Engram evaluates the visible conversation and saves only high-confidence facts that are likely to remain useful for months. It does not save a general session summary.

## 3. Review the Extraction Result

Claude reports:

- how many facts were saved,
- how many repository or organization facts were submitted for review,
- how many facts failed to save, and
- any proposal IDs for facts awaiting review.

Check that each fact has the correct scope:

- **User** — stable personal preferences, working style, expertise, recurring goals, or long-running projects.
- **Repository** — stable architecture decisions, conventions, testing practices, or implementation patterns for the current repository.
- **Organization** — shared standards or processes that apply across repositories.

> Do not extract temporary tasks, session summaries, current bugs, stack traces, credentials, tokens, secrets, private keys, or low-confidence assumptions.

## 4. Verify the Saved Facts

Open the [Engram dashboard](https://stag.deputydev.ai/engram) and confirm that the saved user facts and any repository or organization review proposals are correct.

---

# Troubleshooting

## Cannot Sign In

- Confirm that Zscaler or the required VPN is connected.
- Confirm that you are signing in with your Tata 1mg Gmail account.
- If authentication still fails, report the issue before proceeding.

## `engram-status` Fails

Verify that:

- a valid, non-revoked Personal Access Token was generated,
- `ENGRAM_PERSONAL_ACCESS_TOKEN` is set,
- the plugin is installed and enabled,
- local MCP server permission was approved when using Claude Desktop,
- Claude was restarted after setting the environment variable,
- Claude Code was launched from a terminal containing the environment variable, and
- `/reload-skills` completed successfully.

## Environment Variable Is Not Detected

Check the current terminal:

```bash
echo $ENGRAM_PERSONAL_ACCESS_TOKEN
```

For Zsh, reload the configuration:

```bash
source ~/.zshrc
```

For Bash, reload the configuration:

```bash
source ~/.bashrc
```

For Fish, check the universal variable:

```fish
set --show ENGRAM_PERSONAL_ACCESS_TOKEN
```

For Claude Desktop, check the macOS GUI environment:

```bash
launchctl getenv ENGRAM_PERSONAL_ACCESS_TOKEN
```

If it is empty, set it again:

```bash
launchctl setenv ENGRAM_PERSONAL_ACCESS_TOKEN "engpat_live_xxxxxxxxxxxxxxxxx"
```

Then quit and relaunch Claude Desktop.

## Plugin Installation Fails

Verify that:

- you are running a recent version of Claude or Claude Code,
- the repository is accessible at [github.com/vaibhavmeena1/engram_backend](https://github.com/vaibhavmeena1/engram_backend),
- your internet connection is working,
- Zscaler or the required VPN is connected, and
- the marketplace was added and synchronized before plugin installation.

## PAT Was Exposed

If a token was pasted into a public location, committed to Git, shared, or shown in a screenshot:

1. Revoke it from [Engram API Keys](https://stag.deputydev.ai/engram/api-keys).
2. Generate a replacement token.
3. Update the shell and `launchctl` environment variables.
4. Restart Claude Desktop or Claude Code.