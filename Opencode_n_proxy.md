# Complete Guide: Installing and Configuring OpenCode with AgentRouter and Codex Strip Proxy on Windows Using WSL2 and Ubuntu

## 1. Introduction

This guide explains how to install and configure OpenCode on a Windows computer using Windows Subsystem for Linux 2 (WSL2) and Ubuntu.

The objective is to allow OpenCode to communicate with AgentRouter through an existing local codex-strip-proxy service running inside Ubuntu.

The proxy is the same service used by the ChatGPT desktop application's Codex functionality.

It acts as an intermediary between OpenCode and AgentRouter, forwarding OpenAI Responses API requests while removing selected server-specific conversation state that can cause cross-resource Azure OpenAI errors.

By following this guide, you will:

- Install OpenCode inside Ubuntu on WSL2.
- Verify that OpenCode is correctly installed.
- Confirm that the existing Codex Strip Proxy is running.
- Configure your AgentRouter API key in Ubuntu.
- Make the API key available automatically whenever Ubuntu starts a Bash session.
- Create OpenCode's configuration directory.
- Configure AgentRouter as a custom OpenCode provider.
- Configure the OpenAI Responses API.
- Register GPT-5.6 Sol and GPT-6.1 Sol.
- Authenticate OpenCode with AgentRouter.
- Verify that both models appear in OpenCode.
- Test authenticated requests through the proxy.
- Inspect proxy logs to confirm successful communication.
- Troubleshoot common installation and authentication problems.

The instructions are written for users who may have little or no previous experience with Linux.

---

## PART ONE: UNDERSTANDING THE ARCHITECTURE

### 2. How the system works

Before installing anything, it is useful to understand how the different components communicate.

In this setup:

- Windows runs the computer's main operating system.
- WSL2 provides a Linux environment inside Windows.
- Ubuntu runs OpenCode.
- Ubuntu also runs the existing Codex Strip Proxy.
- AgentRouter provides access to the GPT models.
- The proxy forwards requests between OpenCode and AgentRouter.

The communication architecture is:

```text
Windows 11
    |
    |-- WSL2
          |
          |-- Ubuntu
                |
                |-- OpenCode 2.3.2
                |       |
                |       |-- GPT-5.6 Sol
                |       |
                |       |-- GPT-6.1 Sol
                |       |
                |       v
                |   AgentRouter Provider
                |       |
                |       v
                |   127.0.0.1:8899/v1
                |       |
                |       v
                |   codex-strip-proxy
                |       |
                |       |-- Request sanitization
                |       |
                |       v
                |   https://agentrouter.org
                |       |
                |       v
                |   GPT Model Responses
```

The proxy listens on:

```text
127.0.0.1:8899
```

OpenCode communicates with the proxy using:

```text
http://127.0.0.1:8899/v1
```

Because OpenCode and the proxy both run inside the same Ubuntu environment, they can communicate through localhost.

There is no need to configure Windows-to-WSL port forwarding for OpenCode.

---

### 3. Why use the Responses API?

AgentRouter supports several API protocols through OpenCode.

The main options include:

| Provider package | API protocol |
| --- | --- |
| `@ai-sdk/openai-compatible` | OpenAI Chat Completions |
| `@ai-sdk/openai` | OpenAI Responses API |
| `@ai-sdk/anthropic` | Anthropic Messages API |

This installation uses:

```text
@ai-sdk/openai
```

This is important because the Codex Strip Proxy is designed to process requests sent to:

```text
/v1/responses
```

Using a different API protocol could bypass the sanitizer or produce incompatible requests.

Therefore, use the OpenAI Responses API provider.

---

## PART TWO: PREPARING UBUNTU

### 4. Open Ubuntu

First, open Ubuntu from the Windows Start menu.

1. Click the Windows Start button.
2. Search for Ubuntu.
3. Click the Ubuntu application.
4. Wait for the terminal to open.

You should see a prompt similar to:

```text
victoria_university@DESKTOP-AUS75J2:~$
```

The exact computer name and username may differ.

This is the Ubuntu terminal.

All Linux commands in this guide must be entered here unless explicitly identified as Windows PowerShell commands.

#### Understanding the terminal prompt

For example:

```text
victoria_university@DESKTOP-AUS75J2:~/codex-strip-proxy-setup$
```

This tells you:

- `victoria_university` is your Ubuntu username.
- `DESKTOP-AUS75J2` is your computer name.
- `~/codex-strip-proxy-setup` is your current directory.
- `$` indicates that Ubuntu is ready to receive a command.

Do not confuse the Ubuntu terminal with Windows PowerShell.

Linux and PowerShell use different command languages.

---

### 5. Check whether WSL and Ubuntu are working

Open Windows PowerShell and run:

```powershell
wsl --list --verbose
```

You should see Ubuntu listed.

For example:

```text
NAME      STATE     VERSION
Ubuntu    Running   2
```

The important value is:

```text
VERSION 2
```

This confirms that Ubuntu is running under WSL2.

Return to Ubuntu after completing the check.

---

## PART THREE: VERIFYING THE EXISTING CODEX STRIP PROXY

### 6. Understand why the existing proxy is important

This guide assumes that codex-strip-proxy has already been installed using the separate Codex Strip Proxy installation guide.

We are reusing that existing service.

There is no need to install another proxy for OpenCode.

The proxy must be running before OpenCode can communicate through it.

---

### 7. Check the proxy service

Inside Ubuntu, run:

```bash
systemctl --user status codex-strip-proxy --no-pager
```

A successful result should contain:

```text
Active: active (running)
```

You should also see something similar to:

```text
codex strip proxy: 127.0.0.1:8899 -> https://agentrouter.org
```

This confirms that the proxy is running and forwarding requests to AgentRouter.

#### What if the proxy is stopped?

Run:

```bash
systemctl --user start codex-strip-proxy
```

Then check again:

```bash
systemctl --user status codex-strip-proxy --no-pager
```

Do not reinstall the proxy if it is already installed and functioning.

---

### 8. Verify the listening port

Run:

```bash
ss -ltnp 'sport = :8899'
```

The expected listening address is:

```text
127.0.0.1:8899
```

This is important.

The proxy should listen on the local loopback address rather than being exposed directly to the wider network.

---

### 9. Check the proxy logs

Run:

```bash
tail -n 10 ~/.local/state/codex-strip-proxy/proxy.log
```

The log may contain previous requests.

For example:

```text
2026-11-18 10:25:38 /v1/responses http=200 stripped=0 req=2369B
```

The important fields are:

- **http=200:** The upstream request succeeded.
- **stripped=0:** No matching fields needed removal in that request.
- **req=2369B:** The request body contained 2,369 bytes.

A proxy log showing previous HTTP 200 responses is evidence that the service has successfully processed requests.

---

## PART FOUR: INSTALLING OPENCODE

### 10. Check whether OpenCode is already installed

Inside Ubuntu, run:

```bash
opencode --version
```

During our installation, the output was:

```text
opencode v2.3.2
```

If OpenCode is already installed and the version command works, you do not need to reinstall it.

If OpenCode is not installed, proceed to the next step.

---

### 11. Install OpenCode

Inside Ubuntu, run:

```bash
curl -fsSL https://opencode.ai/install | bash
```

This downloads and executes the official OpenCode installation script.

Wait for the installation to complete.

If the command reports that curl is missing, install it:

```bash
sudo apt update
sudo apt install curl -y
```

Then repeat the OpenCode installation command.

> **Important:** Install OpenCode inside Ubuntu. Do not install it in Windows PowerShell if your intention is to run it inside WSL2.

---

### 12. Verify the installation

Run:

```bash
opencode --version
```

Expected:

```text
opencode v2.3.2
```

Your version may differ if a newer release has been installed.

The important thing is that OpenCode starts successfully.

---

## PART FIVE: CONFIGURING THE AGENTROUTER API KEY

### 13. Understand the API key

AgentRouter requires an API key to authenticate requests.

Without a valid API key, OpenCode may successfully communicate with the local proxy but AgentRouter will reject the request.

For example, the proxy may return:

```text
http=401
```

An authentication error from AgentRouter may also display:

```text
未提供令牌
```

This Chinese message means:

```text
No token provided.
```

We encountered this during the initial OpenCode testing.

The problem was resolved by authenticating the AgentRouter provider through OpenCode.

In addition, we configured the API key as an Ubuntu Bash environment variable.

---

### 14. Open the Bash configuration file

Ubuntu uses a file called:

```text
~/.bashrc
```

This file contains commands that Bash executes when an interactive terminal starts.

We will use it to make the AgentRouter API key available automatically.

Inside Ubuntu, run:

```bash
nano ~/.bashrc
```

This opens the Nano text editor.

---

### 15. Add the AgentRouter API key

Move to the bottom of the file.

Add the following line:

```bash
export CODEX_GATEWAY_API_KEY="YOUR_ACTUAL_AGENTROUTER_API_KEY"
```

Replace:

```text
YOUR_ACTUAL_AGENTROUTER_API_KEY
```

with your actual AgentRouter API key.

Do not include the example text as your real key.

For example, the command should have this structure:

```bash
export CODEX_GATEWAY_API_KEY="your-real-secret-key"
```

Do not share the key in screenshots, documents, public repositories or conversations.

#### Important security considerations

The key is stored as plaintext in your Ubuntu `.bashrc` file.

Keep your Ubuntu account secure.

Restrict access to the file:

```bash
chmod 600 ~/.bashrc
```

This ensures that only your Ubuntu user can read and modify the file.

Avoid adding multiple copies of the same export command.

If the variable is already present in `.bashrc`, update the existing line instead of creating duplicates.

---

### 16. Save the Bash configuration

In Nano:

1. Press `Ctrl + O`.
2. Press `Enter` to confirm the filename.
3. Press `Ctrl + X` to exit.

You will return to the Ubuntu terminal.

---

### 17. Reload Bash

Run:

```bash
source ~/.bashrc
```

This reloads your Bash configuration without requiring you to close the terminal.

The API key should now be available in the current terminal session.

---

### 18. Verify that the API key is available

Run:

```bash
if [ -n "$CODEX_GATEWAY_API_KEY" ]; then
    echo "AgentRouter API key available"
else
    echo "AgentRouter API key missing"
fi
```

Expected:

```text
AgentRouter API key available
```

Do not run:

```bash
echo "$CODEX_GATEWAY_API_KEY"
```

That command displays the actual secret.

#### Important: Use the correct terminal commands

The previous verification command uses Bash syntax.

It must be executed inside Ubuntu.

Do not execute it in Windows PowerShell.

PowerShell uses a different syntax:

```powershell
if ($env:CODEX_GATEWAY_API_KEY) {
    Write-Host "API key available"
}
```

For this installation, use the Ubuntu Bash version.

---

## PART SIX: CREATING OPENCODE'S CONFIGURATION

### 19. Understand the OpenCode configuration directory

OpenCode has its own configuration directory.

The default location is:

```text
/home/victoria_university/.config/opencode/
```

This is different from the Windows Codex configuration directory:

```text
C:\Users\VICTORIA UNIVERSITY\.codex\
```

Do not modify the Windows Codex configuration when setting up OpenCode.

The two applications use separate configuration files.

---

### 20. Create the OpenCode configuration directory

Inside Ubuntu, run:

```bash
mkdir -p ~/.config/opencode
```

This creates the directory if it does not already exist.

The `-p` option prevents an error if the directory already exists.

---

### 21. Check the directory

Run:

```bash
ls -la ~/.config/opencode/
```

Before creating the configuration file, you may see files such as:

```text
cli.json
service.json
```

These are existing OpenCode files.

Do not delete them.

We will create a separate configuration file.

---

### 22. Create opencode.json

Run:

```bash
nano ~/.config/opencode/opencode.json
```

This opens a new configuration file.

We will now configure AgentRouter as a custom provider.

---

## PART SEVEN: CONFIGURING AGENTROUTER

### 23. Understand the AgentRouter provider settings

AgentRouter supports custom providers in OpenCode.

The configuration includes:

| Setting | Purpose |
| --- | --- |
| `provider` | Defines custom providers |
| `npm` | Specifies the Vercel AI SDK provider package |
| `name` | Sets the provider's display name |
| `options.baseURL` | Defines the API endpoint |
| `options.apiKey` | Specifies the API authentication key |
| `models` | Registers available models |
| `model` | Selects the default model |

For this installation, we use:

```text
@ai-sdk/openai
```

This selects the OpenAI Responses API implementation.

We do not use:

```text
@ai-sdk/openai-compatible
```

That package uses the Chat Completions protocol, which is not the intended protocol for this proxy setup.

---

### 24. Enter the OpenCode configuration

Insert the following complete configuration into:

```text
~/.config/opencode/opencode.json
```

```json
{
  "$schema": "https://opencode.ai/config.json",
  "provider": {
    "AgentRouter-openai-gateway": {
      "npm": "@ai-sdk/openai",
      "name": "AgentRouter via Codex Strip Proxy",
      "options": {
        "baseURL": "http://127.0.0.1:8899/v1",
        "apiKey": "{env:CODEX_GATEWAY_API_KEY}"
      },
      "models": {
        "gpt-5.6-sol": {
          "name": "GPT-5.6 Sol"
        },
        "gpt-6.1-sol": {
          "name": "GPT-6.1 Sol"
        }
      }
    }
  },
  "model": "AgentRouter-openai-gateway/gpt-6.1-sol"
}
```

#### Understanding the configuration

**Provider name:**

```json
"AgentRouter-openai-gateway"
```

This is the identifier OpenCode uses for the custom provider.

**Provider package:**

```json
"npm": "@ai-sdk/openai"
```

This selects the OpenAI Responses API implementation.

**Provider URL:**

```json
"baseURL": "http://127.0.0.1:8899/v1"
```

This sends requests to the local Codex Strip Proxy rather than directly to AgentRouter.

**API key:**

```json
"apiKey": "{env:CODEX_GATEWAY_API_KEY}"
```

This references the API key stored in the Ubuntu environment variable.

**Registered models:**

```json
"gpt-5.6-sol"
"gpt-6.1-sol"
```

These are the two model identifiers that were successfully tested in our installation.

**Default model:**

```json
"model": "AgentRouter-openai-gateway/gpt-6.1-sol"
```

This tells OpenCode to use GPT-6.1 Sol by default.

You can change the default to GPT-5.6 Sol if preferred.

#### Important model availability note

AgentRouter's available model catalogue can change.

Always verify that the exact model identifier is supported by your account.

The model identifier must match the provider's supported model name.

An unavailable model may produce HTTP 503 errors even when the proxy and authentication are working correctly.

---

### 25. Save the configuration

In Nano:

1. Press `Ctrl + O`.
2. Press `Enter`.
3. Press `Ctrl + X`.

The OpenCode configuration is now saved.

---

### 26. Validate the JSON configuration

Before launching OpenCode, verify that the configuration is valid JSON.

Run:

```bash
python3 -m json.tool ~/.config/opencode/opencode.json
```

If successful, Python prints the formatted configuration.

If you see an error such as:

```text
Expecting property name enclosed in double quotes
```

the JSON contains a formatting problem.

Common causes include:

- Missing commas.
- Missing quotation marks.
- Extra commas.
- Incorrect braces.

Correct the file using:

```bash
nano ~/.config/opencode/opencode.json
```

Then repeat the validation.

---

## PART EIGHT: AUTHENTICATING OPENCODE WITH AGENTROUTER

### 27. Launch OpenCode

Inside Ubuntu, run:

```bash
opencode
```

OpenCode should start.

You should see its interactive interface.

The default model should be:

```text
GPT-6.1 Sol
```

---

### 28. Connect to AgentRouter

Although the API key is referenced in the configuration, we also completed the provider authentication through OpenCode.

Inside OpenCode, enter:

```text
/connect
```

This opens the provider connection interface.

Follow these steps:

1. Find `AgentRouter-openai-gateway`.
2. Select the provider.
3. Choose API key authentication if prompted.
4. Enter your actual AgentRouter API key.
5. Confirm the connection.

Do not share your API key.

OpenCode saves the authentication information using its credential management.

#### Why this step matters

During our initial testing, OpenCode displayed:

```text
未提供令牌
```

The proxy logs showed:

```text
http=401
```

This meant that OpenCode was reaching AgentRouter through the proxy, but the upstream service was not receiving valid authentication.

After connecting through `/connect` and supplying the API key, requests began succeeding.

---

## PART NINE: VERIFYING MODEL DISCOVERY

### 29. Check the available models

Inside OpenCode, enter:

```text
/models
```

OpenCode should display the models registered under the custom AgentRouter provider.

Look for:

```text
AgentRouter-openai-gateway/gpt-5.6-sol
```

and:

```text
AgentRouter-openai-gateway/gpt-6.1-sol
```

Both models should be selectable.

#### What if the models do not appear?

Check the following:

- Confirm that `opencode.json` is in the correct directory.
- Confirm that the provider uses the singular `"provider"` configuration key.
- Confirm that the model identifiers are spelled correctly.
- Validate the JSON using Python.
- Restart OpenCode.
- Run `/models` again.

The correct configuration location is:

```text
~/.config/opencode/opencode.json
```

Do not confuse this with:

```text
~/.codex/config.toml
```

The latter belongs to Codex.

---

## PART TEN: TESTING AUTHENTICATED COMMUNICATION

### 30. Start monitoring the proxy logs

Before sending test prompts, open a second Ubuntu terminal.

You can open another Ubuntu window from the Windows Start menu.

In the second terminal, run:

```bash
tail -n 0 -F ~/.local/state/codex-strip-proxy/proxy.log
```

This command displays new proxy log entries as they arrive.

Keep the terminal open.

Do not close it while testing.

#### Understanding the command

- `tail` displays file contents.
- `-n 0` starts from new entries only.
- `-F` continues following the log file.

To stop monitoring later, press:

```text
Ctrl + C
```

This only stops the log viewer.

It does not stop the proxy service.

---

### 31. Test GPT-5.6 Sol

Return to the first Ubuntu terminal.

If OpenCode is not running, launch it:

```bash
opencode
```

Inside OpenCode, enter:

```text
/models
```

Select:

```text
GPT-5.6 Sol
```

Send this test prompt:

```text
What is 125 multiplied by 8? Explain your calculation.
```

Expected response:

```text
125 × 8 = 1,000.

Calculation:

100 × 8 = 800

25 × 8 = 200

800 + 200 = 1,000.
```

#### Verify the proxy logs

Return to the second Ubuntu terminal.

You should see successful requests similar to:

```text
2026-11-18 10:25:38 /v1/responses http=200 stripped=0 req=2369B
2026-11-18 10:25:40 /v1/responses http=200 stripped=0 req=26578B
```

The important result is:

```text
http=200
```

This confirms that the upstream request succeeded.

---

### 32. Test GPT-6.1 Sol

Now return to OpenCode.

Enter:

```text
/models
```

Select:

```text
GPT-6.1 Sol
```

Send:

```text
What is 144 multiplied by 25? Explain your calculation.
```

Expected response:

```text
144 × 25 = 3,600.

Since 25 is one-quarter of 100:

144 × 100 = 14,400

14,400 ÷ 4 = 3,600.
```

#### Verify the proxy logs

The successful installation produced:

```text
2026-11-18 10:31:04 /v1/responses http=200 stripped=0 req=26450B
2026-11-18 10:31:05 /v1/responses http=200 stripped=0 req=2370B
```

This confirmed that GPT-6.1 Sol successfully communicated with AgentRouter through the proxy.

---

## PART ELEVEN: UNDERSTANDING THE PROXY LOGS

### 33. What does HTTP 200 mean?

Example:

```text
/v1/responses http=200 stripped=0 req=26450B
```

This means:

- The request reached the proxy.
- The proxy forwarded the request to AgentRouter.
- AgentRouter successfully processed the request.
- The upstream returned HTTP 200.
- The request body contained 26,450 bytes.

HTTP 200 is the expected successful response.

---

### 34. What does stripped=0 mean?

You may notice:

```text
stripped=0
```

This is not an error.

It means the sanitizer did not find any matching fields to remove in that particular request.

The proxy does not need to remove fields from every request.

When matching fields are present, the stripping count may be greater than zero.

For example:

```text
http=200 stripped=5
```

This means five matching fields were removed from that individual request.

It does not mean five messages were deleted.

---

### 35. What does HTTP 401 mean?

Example:

```text
http=401 stripped=0
```

This indicates an authentication failure.

During our installation, this occurred before we connected the AgentRouter provider through OpenCode.

The error displayed:

```text
未提供令牌
```

Meaning:

```text
No token provided.
```

The solution was to authenticate using:

```text
/connect
```

and provide the AgentRouter API key.

---

### 36. What does HTTP 503 mean?

HTTP 503 indicates that the upstream service could not fulfil the request.

Possible causes include:

- An unavailable model.
- No available provider channel.
- Temporary AgentRouter service problems.
- Upstream resource availability issues.

Do not immediately assume that HTTP 503 is caused by WSL or the local proxy.

Check whether other requests are succeeding.

---

## PART TWELVE: TESTING CONVERSATION FOLLOW-UPS

### 37. Why follow-up testing matters

A successful first prompt proves that a model can respond.

However, we also want to verify that OpenCode can continue a conversation.

The Responses API supports conversation-related state, and this proxy is designed to remove selected resource-specific state before forwarding requests.

Therefore, test a second prompt in the same conversation.

---

### 38. Send the first prompt

In OpenCode, send:

```text
What is 144 multiplied by 25? Explain your calculation.
```

The expected answer is:

```text
3,600
```

---

### 39. Send the follow-up prompt

Without starting a new conversation, send:

```text
What calculation did I ask you to perform previously, and what was the answer?
```

Expected response:

```text
You asked me to calculate 144 multiplied by 25.

The answer was 3,600.
```

This verifies that the model can use the available conversation context.

---

### 40. Verify the new proxy logs

Check the second terminal.

You should see additional entries for the follow-up request.

Successful entries should contain:

```text
/v1/responses http=200
```

A positive stripping count may appear when the request contains matching server-specific state.

The presence of HTTP 200 entries confirms successful upstream processing.

---

## PART THIRTEEN: TROUBLESHOOTING

### 41. Problem: OpenCode command not found

Example:

```text
opencode: command not found
```

This means Ubuntu cannot locate the OpenCode executable.

Check:

```bash
opencode --version
```

If OpenCode is not installed, run:

```bash
curl -fsSL https://opencode.ai/install | bash
```

If it was installed but is not available in the current terminal, reopen Ubuntu and try again.

---

### 42. Problem: API key missing

Run:

```bash
if [ -n "$CODEX_GATEWAY_API_KEY" ]; then
    echo "API key available"
else
    echo "API key missing"
fi
```

If the key is missing, open:

```bash
nano ~/.bashrc
```

Confirm that the following line exists:

```bash
export CODEX_GATEWAY_API_KEY="YOUR_ACTUAL_AGENTROUTER_API_KEY"
```

Save the file and run:

```bash
source ~/.bashrc
```

Repeat the verification.

---

### 43. Problem: PowerShell commands entered into Ubuntu

An error such as:

```text
Write-Host: command not found
```

means that a PowerShell command was entered into Ubuntu.

PowerShell and Bash use different syntax.

Use the following distinction:

| Task | Correct environment |
| --- | --- |
| `systemctl` | Ubuntu |
| `nano ~/.bashrc` | Ubuntu |
| `opencode` | Ubuntu |
| `tail` | Ubuntu |
| `wsl --list --verbose` | Windows PowerShell |
| `wsl --shutdown` | Windows PowerShell |
| `$env:VARIABLE` | Windows PowerShell |
| `$VARIABLE` | Ubuntu Bash |

Always check your terminal prompt before entering commands.

Ubuntu normally displays something similar to:

```text
victoria_university@DESKTOP-AUS75J2:~$
```

PowerShell normally displays:

```text
PS C:\Users\...
```

---

### 44. Problem: OpenCode models do not appear

First, verify the configuration file exists:

```bash
ls -l ~/.config/opencode/opencode.json
```

Validate the JSON:

```bash
python3 -m json.tool ~/.config/opencode/opencode.json
```

Check that the provider configuration uses:

```json
"provider": {
```

Not:

```json
"providers": {
```

Confirm the registered models:

```json
"models": {
  "gpt-5.6-sol": {
    "name": "GPT-5.6 Sol"
  },
  "gpt-6.1-sol": {
    "name": "GPT-6.1 Sol"
  }
}
```

Exit OpenCode and restart it.

Then run:

```text
/models
```

---

### 45. Problem: AgentRouter returns HTTP 401

Example:

```text
http=401
```

Possible message:

```text
未提供令牌
```

Meaning:

```text
No token provided.
```

Check the API key variable:

```bash
if [ -n "$CODEX_GATEWAY_API_KEY" ]; then
    echo "API key available"
else
    echo "API key missing"
fi
```

Then enter OpenCode:

```bash
opencode
```

Run:

```text
/connect
```

Select:

```text
AgentRouter-openai-gateway
```

Choose API key authentication if requested.

Enter your AgentRouter API key and confirm.

Retry your prompt.

Check the logs for HTTP 200.

---

### 46. Problem: AgentRouter returns HTTP 503

A 503 response may indicate that the model identifier is unavailable.

Check the exact model identifier in your AgentRouter personal console.

Use:

```text
https://ps.air-outer.com/console/personal
```

Confirm that the model is available to your account.

For this installation, the following identifiers were successfully tested:

```text
gpt-5.6-sol
gpt-6.1-sol
```

Do not change the proxy merely because one model returns HTTP 503.

---

### 47. Problem: Proxy is not running

Run:

```bash
systemctl --user status codex-strip-proxy --no-pager
```

If it is stopped:

```bash
systemctl --user start codex-strip-proxy
```

Check the port:

```bash
ss -ltnp 'sport = :8899'
```

Expected:

```text
127.0.0.1:8899
```

---

### 48. Problem: OpenCode cannot connect to the proxy

Confirm that the configuration contains:

```json
"baseURL": "http://127.0.0.1:8899/v1"
```

Do not use:

```text
https://127.0.0.1:8899/v1
```

The local proxy uses HTTP, not HTTPS.

Check the service and port again.

---

### 49. Problem: OpenCode works, but the proxy log does not show requests

Check that OpenCode is using:

```text
http://127.0.0.1:8899/v1
```

It should not use:

```text
https://agentrouter.org/v1
```

The latter bypasses the local proxy.

Also confirm that the provider package is:

```text
@ai-sdk/openai
```

This ensures the intended Responses API implementation is used.

---

## PART FOURTEEN: FINAL VERIFICATION CHECKLIST

### 50. Installation checklist

Use this checklist to determine whether the setup is complete.

#### Ubuntu and WSL2

- [ ] WSL2 installed and working.
- [ ] Ubuntu installed.
- [ ] Ubuntu terminal accessible.
- [ ] OpenCode installed inside Ubuntu.
- [ ] OpenCode version verified.
- [ ] Existing Codex Strip Proxy installation preserved.

#### Proxy verification

- [ ] Proxy service enabled.
- [ ] Proxy service running.
- [ ] Proxy listening on `127.0.0.1:8899`.
- [ ] Proxy forwarding to AgentRouter.
- [ ] Proxy logs accessible.

#### API key configuration

- [ ] AgentRouter API key obtained.
- [ ] API key added to Ubuntu `.bashrc`.
- [ ] Bash configuration saved.
- [ ] Bash configuration reloaded.
- [ ] API key availability verified.
- [ ] API key not exposed in logs or screenshots.

#### OpenCode configuration

- [ ] `~/.config/opencode/` directory created.
- [ ] `opencode.json` created.
- [ ] AgentRouter provider configured.
- [ ] OpenAI Responses API selected.
- [ ] Local proxy URL configured.
- [ ] API key environment variable referenced.
- [ ] GPT-5.6 Sol registered.
- [ ] GPT-6.1 Sol registered.
- [ ] JSON syntax validated.

#### Authentication

- [ ] OpenCode launched successfully.
- [ ] `/connect` executed.
- [ ] AgentRouter provider selected.
- [ ] API key supplied.
- [ ] Provider authentication completed.

#### Functional testing

- [ ] Both models appear in `/models`.
- [ ] GPT-5.6 Sol responds successfully.
- [ ] GPT-6.1 Sol responds successfully.
- [ ] GPT-5.6 Sol request returned HTTP 200.
- [ ] GPT-6.1 Sol request returned HTTP 200.
- [ ] Proxy logs show `/v1/responses`.
- [ ] Conversation follow-up tested.
- [ ] Correct answers received.
- [ ] No authentication errors during successful tests.

---

## PART FIFTEEN: ACTUAL INSTALLATION RESULTS

### 51. Results from the completed installation

The following results were observed during the actual configuration.

#### OpenCode version

```text
opencode v2.3.2
```

#### Proxy service

```text
Active: active (running)
```

#### Proxy listening address

```text
127.0.0.1:8899
```

#### AgentRouter provider

```text
AgentRouter-openai-gateway
```

#### Configured API endpoint

```text
http://127.0.0.1:8899/v1
```

#### Configured API protocol

```text
OpenAI Responses API
```

#### Registered models

```text
GPT-5.6 Sol
GPT-6.1 Sol
```

#### GPT-5.6 Sol functional test

Prompt:

```text
What is 125 multiplied by 8? Explain your calculation.
```

Actual response:

```text
125 × 8 = 1,000.

Calculation:

100×8 + 25×8 = 800 + 200 = 1,000.
```

Proxy logs:

```text
2026-11-18 10:25:38 /v1/responses http=200 stripped=0 req=2369B
2026-11-18 10:25:40 /v1/responses http=200 stripped=0 req=26578B
```

**Result: Successful.**

#### GPT-6.1 Sol functional test

Prompt:

```text
What is 144 multiplied by 25? Explain your calculation.
```

Actual response:

```text
144 × 25 = 3,600.

Since 25 is one-quarter of 100, multiply 144 by 100 to get 14,400, then divide by 4:

14,400 ÷ 4 = 3,600.
```

Proxy logs:

```text
2026-11-18 10:31:04 /v1/responses http=200 stripped=0 req=26450B
2026-11-18 10:31:05 /v1/responses http=200 stripped=0 req=2370B
```

**Result: Successful.**

These results demonstrate that both configured models successfully processed authenticated Responses API requests through the local proxy.

---

## PART SIXTEEN: MAINTENANCE

### 52. Starting OpenCode

Whenever you want to use OpenCode:

1. Open Ubuntu.
2. Confirm the proxy is running.
3. Launch OpenCode.

Commands:

```bash
systemctl --user status codex-strip-proxy --no-pager
```

Then:

```bash
opencode
```

---

### 53. Checking the models

Inside OpenCode:

```text
/models
```

Select either GPT-5.6 Sol or GPT-6.1 Sol.

---

### 54. Monitoring proxy activity

Inside another Ubuntu terminal:

```bash
tail -n 20 ~/.local/state/codex-strip-proxy/proxy.log
```

To monitor new activity continuously:

```bash
tail -n 0 -F ~/.local/state/codex-strip-proxy/proxy.log
```

---

### 55. Restarting the proxy

If necessary:

```bash
systemctl --user restart codex-strip-proxy
```

Check:

```bash
systemctl --user status codex-strip-proxy --no-pager
```

---

### 56. Important maintenance precautions

- Keep your AgentRouter API key private.
- Do not delete the existing Codex Strip Proxy installation.
- Do not modify the Windows Codex configuration unnecessarily.
- Keep the OpenCode configuration in `~/.config/opencode/opencode.json`.
- Keep the API key environment variable name consistent.
- Do not expose the proxy on a public network interface.
- Verify model availability when adding new models.
- Monitor repeated HTTP 401 and HTTP 503 errors.
- Do not confuse a model availability problem with a proxy connectivity problem.

---

### 57. Final conclusion

OpenCode was successfully installed and configured inside Ubuntu running under Windows Subsystem for Linux 2.

The existing codex-strip-proxy service was reused rather than installing another proxy.

AgentRouter authentication was configured through Ubuntu's Bash environment and OpenCode's provider authentication interface.

OpenCode was configured to use the OpenAI Responses API through:

```text
http://127.0.0.1:8899/v1
```

Two models were successfully registered and tested:

```text
GPT-5.6 Sol
GPT-6.1 Sol
```

Both models returned correct answers to actual prompts.

The proxy logs confirmed successful authenticated requests:

```text
/v1/responses http=200
```

The final architecture is:

```text
Windows 11
    |
    |-- WSL2
          |
          |-- Ubuntu
                |
                |-- OpenCode 2.3.2
                |       |
                |       |-- GPT-5.6 Sol
                |       |
                |       |-- GPT-6.1 Sol
                |       |
                |       v
                |   AgentRouter
                |   Provider Configuration
                |       |
                |       v
                |   Responses API
                |       |
                |       v
                |   127.0.0.1:8899
                |       |
                |       v
                |   codex-strip-proxy
                |       |
                |       |-- Request Sanitization
                |       |
                |       v
                |   https://agentrouter.org
                |       |
                |       v
                |   Authenticated Model Requests
                |       |
                |       v
                |   GPT Model Responses
```

**Final outcome:** OpenCode successfully communicates with AgentRouter through the existing Codex Strip Proxy, with both GPT-5.6 Sol and GPT-6.1 Sol verified using successful HTTP 200 responses.

The installation and two-model connectivity tests have been completed successfully.

A separate multi-turn conversation replay test is recommended before claiming full conversation-state sanitization verification.

---

*End of guide.*
