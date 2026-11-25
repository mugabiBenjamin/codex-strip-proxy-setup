# Complete Guide: Installing and Configuring Codex Strip Proxy on Windows Using WSL2 and Ubuntu

## 1. Introduction

This guide explains how to install and configure codex-strip-proxy on a Windows computer using Windows Subsystem for Linux 2 (WSL2) and Ubuntu.

The objective is to allow the ChatGPT desktop application's Codex functionality to communicate with AgentRouter through a local proxy running inside Ubuntu.

The proxy helps resolve cross-resource Azure OpenAI Responses API errors by removing certain server-specific conversation state before requests are forwarded to AgentRouter.

By following this guide, you will:

- Configure your AgentRouter API credentials in Windows.
- Configure the Codex desktop application's provider settings.
- Enable Windows Subsystem for Linux 2.
- Install Ubuntu.
- Enable systemd inside Ubuntu.
- Install the required Linux tools.
- Download and verify the proxy repository.
- Configure Ubuntu to access your existing Windows Codex configuration.
- Install the proxy as a Linux systemd user service.
- Connect the Windows ChatGPT desktop application to the Ubuntu proxy.
- Test authenticated requests and conversation follow-ups.
- Verify that the proxy is removing replayed state.

The instructions are written for someone who may have little or no previous experience with Linux.

---

## PART ONE: PREPARING WINDOWS

### 2. Configure the AgentRouter API key

Before installing the proxy, you need an AgentRouter API key.

The API key authenticates your requests to AgentRouter.

You can obtain your key from your AgentRouter account.

Keep this key private. Do not share it in screenshots, documents, public repositories or conversations.

#### Step 1: Open PowerShell as Administrator

1. Click the Windows Start button.
2. Search for PowerShell.
3. Right-click Windows PowerShell.
4. Select Run as administrator.
5. Approve the Windows permission prompt if one appears.

#### Step 2: Save the API key as a Windows user environment variable

Copy the following command into PowerShell:

```powershell
[Environment]::SetEnvironmentVariable(
    "CODEX_GATEWAY_API_KEY",
    "replace-with-your-agent-router-api-key",
    "User"
)
```

Replace:

```text
replace-with-your-agent-router-api-key
```

with your actual AgentRouter API key.

For example, the command has the following structure:

```powershell
[Environment]::SetEnvironmentVariable(
    "CODEX_GATEWAY_API_KEY",
    "YOUR_ACTUAL_API_KEY",
    "User"
)
```

Do not use the example text as your actual API key.

**What does this command do?**

It saves your API key in Windows under your user environment variables.

This means applications running under your Windows user account can access the variable without you having to manually enter the API key every time.

The `"User"` parameter means the variable belongs to your Windows user account, rather than being configured system-wide.

#### Step 3: Confirm that the environment variable exists

Close PowerShell completely.

Open a new PowerShell window.

Run:

```powershell
$env:CODEX_GATEWAY_API_KEY
```

If the environment variable is correctly configured, PowerShell will display your API key.

Do not share that output with anyone.

If nothing appears, repeat Step 2 and make sure you entered the correct command.

> **Important:** The API key is separate from your Windows sign-in password. Configuring it does not change how you sign into Windows.

---

### 3. Configure the Codex desktop application's provider

The next step is to configure Codex to use AgentRouter.

The ChatGPT desktop application stores its Codex configuration in:

```text
C:\Users\YOUR_WINDOWS_USERNAME\.codex\config.toml
```

In this installation, the actual location is:

```text
C:\Users\VICTORIA UNIVERSITY\.codex\config.toml
```

#### Step 1: Open the configuration file

1. Open Windows File Explorer.
2. Navigate to:

```text
C:\Users\VICTORIA UNIVERSITY\.codex
```

1. Find:

```text
config.toml
```

1. Open it using Notepad or another plain-text editor.

If Windows asks which application to use, choose Notepad.

#### Step 2: Understand the provider configuration

The relevant configuration is:

```toml
model = "gpt-5.6-sol"
model_provider = "AgentRouter"

[model_providers.AgentRouter]
base_url = "https://agentrouter.org/v1"
env_key = "CODEX_GATEWAY_API_KEY"
name = "AgentRouter"
wire_api = "responses"

[model_providers.AgentRouter.models]
"gpt-5.6-sol" = { name = "GPT-5.6 Sol" }
"gpt-6.1-sol" = { name = "GPT-6.1 Sol" }
"gpt-6.2-astra" = { name = "GPT-6.2 Astra" }
"gpt-6.2-sol" = { name = "GPT-6.2 Sol" }
```

Here is what the important settings mean:

- **model:** The model Codex should use.
- **model_provider:** The provider Codex should select.
- **base_url:** The address to which Codex sends API requests.
- **env_key:** The name of the Windows environment variable containing your API key.
- **wire_api:** Specifies the Responses API format.

#### Step 3: Save the provider configuration

Make sure the provider configuration exists in your file.

> **Important:** If your existing `config.toml` already contains plugins, MCP servers, desktop settings or other configuration, do not delete the entire file and replace it with this short example.

Preserve the existing settings.

Only add missing provider settings or update the relevant existing settings. Avoid creating duplicate TOML sections.

At this stage, the provider URL should be:

```toml
base_url = "https://agentrouter.org/v1"
```

The proxy installer will change this later.

Save the file.

---

## PART TWO: INSTALLING WSL2 AND UBUNTU

### 4. Understand what WSL2 does

Windows Subsystem for Linux (WSL) allows you to run a Linux environment directly inside Windows.

WSL2 is the newer architecture that runs Linux using a lightweight virtual machine.

For this project:

- Windows runs the ChatGPT desktop application.
- Ubuntu runs the proxy.
- WSL2 provides communication between Windows and Ubuntu.
- systemd manages the proxy as a background service.

You do not need to install a separate virtual machine application.

---

### 5. Install WSL2

#### Step 1: Open PowerShell as Administrator

1. Click Start.
2. Search for PowerShell.
3. Right-click it.
4. Select Run as administrator.

#### Step 2: Install Ubuntu

Run:

```powershell
wsl --install -d Ubuntu
```

This command installs WSL and the Ubuntu Linux distribution.

The installation may take several minutes.

You should see messages similar to:

```text
Downloading: Ubuntu

Installing: Ubuntu

Distribution successfully installed.

Launching Ubuntu...
```

If Windows asks you to restart, restart the computer.

#### Step 3: Create your Ubuntu username

After installation, Ubuntu will ask:

```text
Create a default Unix user account:
```

Enter a username.

For this installation, the username was:

```text
victoria_university
```

Ubuntu will then ask you to create a password.

```text
New password:
Retype new password:
```

Create a password of your choice.

> **Important:** This is a Linux password. It does not change your Windows password.

Also, Ubuntu does not display characters while you type a password. You will not see dots or asterisks. This is normal.

Type the password and press Enter.

Type it again when asked and press Enter.

You should eventually see:

```text
passwd: password updated successfully
```

Ubuntu may also ask whether you want to participate in anonymous platform metrics collection.

You can choose `y` or `n`.

Once setup finishes, you are inside Ubuntu.

Your terminal prompt should look similar to:

```text
victoria_university@DESKTOP-AUS75J2:~$
```

This indicates that Ubuntu is running.

---

### 6. Enable systemd inside Ubuntu

systemd is the Linux service manager.

We need it because the proxy will run as a background service managed by Ubuntu.

#### Step 1: Open the WSL configuration file

Inside the Ubuntu terminal, run:

```bash
sudo nano /etc/wsl.conf
```

Ubuntu may ask for your Linux password.

Enter the password you created earlier.

#### Step 2: Add the systemd configuration

Inside the editor, add:

```ini
[boot]
systemd=true
```

If the file already contains other settings, preserve them and add the `[boot]` section only if it does not already exist.

#### Step 3: Save the file

In Nano:

1. Press `Ctrl + O` to save.
2. Press `Enter` to confirm the filename.
3. Press `Ctrl + X` to exit.

#### Step 4: Restart WSL

Open a separate Windows PowerShell window.

Run:

```powershell
wsl --shutdown
```

This shuts down the running WSL instances.

It does not uninstall Ubuntu or delete your files.

#### Step 5: Reopen Ubuntu

Open Ubuntu from the Windows Start menu.

#### Step 6: Verify systemd

Inside Ubuntu, run:

```bash
systemctl --user status
```

A successful result should look similar to:

```text
● DESKTOP-AUS75J2
    State: running
    Units: 169 loaded
    Jobs: 0 queued
    Failed: 0 units
```

You should also see a systemd version.

For example:

```text
systemd: 259.9
```

If you see `State: running`, systemd is working.

**Our installation result:** systemd successfully started and reported zero failed units.

---

## PART THREE: INSTALLING LINUX PREREQUISITES

### 7. Update Ubuntu

Before installing the required tools, update Ubuntu's package information.

Inside Ubuntu, run:

```bash
sudo apt update
```

Wait for the command to finish.

This refreshes the list of available software packages.

---

### 8. Install the required tools

Run:

```bash
sudo apt install git python3 curl iproute2 -y
```

The `-y` option automatically confirms the installation.

The packages are:

| Package  | Purpose                                      |
| -------- | -------------------------------------------- |
| Git      | Downloads and manages the project repository |
| Python3  | Runs the proxy and verification scripts      |
| Curl     | Tests HTTP communication                     |
| iproute2 | Provides Linux networking commands           |

Wait for the installation to finish.

#### Step 9: Verify the installed tools

Run each command:

```bash
git --version
```

```bash
python3 --version
```

```bash
curl --version
```

```bash
ip -V
```

The versions observed during this installation were:

```text
git version 2.53.0

Python 3.14.4

curl 8.18.0

ip utility, iproute2-6.19.0
```

Your versions may differ.

What matters is that all four commands work.

---

## PART FOUR: DOWNLOADING THE PROJECT

### 9. Clone the codex-strip-proxy repository

The project is hosted on GitHub:

[https://github.com/mugabiBenjamin/codex-strip-proxy-setup](https://github.com/mugabiBenjamin/codex-strip-proxy-setup)

#### Important: Work inside the Ubuntu filesystem

This is one of the most important lessons from the installation.

Initially, the repository was cloned under the Windows-mounted directory:

```text
/mnt/c/Users/VICTORIA UNIVERSITY/.codex/
```

When the verification script was executed, it returned:

```text
: invalid option nameine 5: set: pipefail
```

This was caused by the script being checked out with Windows-style line endings.

To avoid this problem, clone the repository inside Ubuntu's own filesystem.

#### Step 1: Move to the Ubuntu home directory

Run:

```bash
cd ~
```

The `~` symbol represents your Ubuntu home directory.

For this installation, it is:

```text
/home/victoria_university
```

#### Step 2: Clone the repository

Run:

```bash
git clone https://github.com/mugabiBenjamin/codex-strip-proxy-setup.git
```

Wait for Git to download the repository.

#### Step 3: Enter the project directory

Run:

```bash
cd codex-strip-proxy-setup
```

#### Step 4: Switch to the main branch

Run:

```bash
git switch main
```

You should now be inside:

```text
/home/victoria_university/codex-strip-proxy-setup
```

#### Step 5: Verify the project files

Run:

```bash
bash ci/verify_files.sh --tracked
```

Expected result:

```text
OK: 27 shipped files exist and are tracked.
```

#### Step 6: Run the unit tests

Run:

```bash
python3 -m unittest discover tests/
```

Expected output:

```text
Ran 39 tests

OK
```

During our installation, the actual output was:

```text
Ran 39 tests in 0.041s

OK (skipped=1)
```

One test was skipped, but there were no failed tests.

Both repository verification and unit tests passed.

---

## PART FIVE: CHECKING CODEX CONFIGURATION

### 10. Check the installation prerequisites

The repository includes a prerequisite verification script.

Run:

```bash
bash ./installer/prereqs.sh
```

During our installation, this command completed without reporting missing prerequisites.

---

### 11. Understand the Windows and Ubuntu configuration difference

This was another important part of the installation.

The ChatGPT desktop application was installed on Windows, not inside Ubuntu.

Its configuration file was located at:

```text
C:\Users\VICTORIA UNIVERSITY\.codex\config.toml
```

However, Ubuntu initially looked for:

```text
/home/victoria_university/.codex/config.toml
```

These are different locations.

That is why this command initially failed:

```bash
/usr/bin/python3 ./bin/proxy-config --mode check
```

The error was:

```text
STOP: Config must be an existing regular file, not a symlink.
```

The expected Ubuntu configuration file did not exist.

We needed to tell Ubuntu where the actual Windows configuration was.

#### Step 1: Locate the Windows configuration from Ubuntu

Windows drives are mounted under `/mnt`.

The Windows C: drive is accessible through:

```text
/mnt/c/
```

Therefore, the Windows Codex configuration can be accessed from Ubuntu at:

```text
/mnt/c/Users/VICTORIA UNIVERSITY/.codex/config.toml
```

Verify that it exists:

```bash
ls -l "/mnt/c/Users/VICTORIA UNIVERSITY/.codex/config.toml"
```

Our result confirmed that it was a regular file.

#### Step 2: Set CODEX_HOME

Run:

```bash
export CODEX_HOME="/mnt/c/Users/VICTORIA UNIVERSITY/.codex"
```

This tells Ubuntu-based installation scripts to use the existing Windows Codex configuration directory.

Verify it:

```bash
echo "$CODEX_HOME"
```

Expected output:

```text
/mnt/c/Users/VICTORIA UNIVERSITY/.codex
```

> **Important:** This export applies to the current Ubuntu shell session. If you close the terminal, you may need to export it again before running installation or configuration commands.

#### Step 3: Check the selected provider

Run:

```bash
/usr/bin/python3 ./bin/proxy-config --mode check
```

Expected result:

```json
{
  "config": "/mnt/c/Users/VICTORIA UNIVERSITY/.codex/config.toml",
  "provider": "AgentRouter",
  "current_url": "https://agentrouter.org/v1",
  "target_url": "http://127.0.0.1:8899/v1",
  "mode": "check",
  "changed": false,
  "status": "preview"
}
```

This confirms that:

- Ubuntu can locate the Windows configuration.
- AgentRouter is recognised.
- The current provider URL is correct.
- The intended local proxy URL is recognised.
- No configuration changes have been made yet.

The check mode is read-only.

---

## PART SIX: REVIEWING THE INSTALLATION

### 12. Understand the installer

Before installation, inspect the main setup script.

Run:

```bash
sed -n '1,180p' installer/setup.sh
```

The script coordinates the installation.

It:

- Loads the pinned proxy version and checksum.
- Determines the Codex configuration directory.
- Checks the selected provider.
- Verifies the project files.
- Downloads and verifies the upstream proxy.
- Installs a systemd user service.
- Runs a forwarding test.
- Updates the selected provider URL.
- Performs final local verification.

The installer must be run as your normal Ubuntu user.

Do not run it with `sudo`.

---

### 13. Inspect the supporting installation files

The following files control important parts of the installation.

#### Service installation script

```bash
sed -n '1,220p' installer/service_install.sh
```

This script downloads the pinned upstream proxy, checks its Git revision and SHA-256 checksum, prepares the systemd service and starts it.

#### Service configuration template

```bash
cat templates/codex-strip-proxy.service.tmpl
```

This template defines how systemd runs the proxy.

The service includes security restrictions such as:

```text
NoNewPrivileges=yes
UMask=0077
ProtectSystem=strict
ProtectHome=read-only
```

It also uses a dedicated writable log directory.

#### Forwarding probe

```bash
sed -n '1,220p' installer/probe.sh
```

This script sends an unauthenticated request directly to AgentRouter and another request through the local proxy.

Both are expected to return HTTP 401 with matching response bodies.

This is intentional.

The probe checks forwarding without exposing or requiring an API key.

---

## PART SEVEN: INSTALLING CODEX STRIP PROXY

### 14. Prepare the Windows Codex configuration

Before running the installer, make sure the environment variable is set:

```bash
export CODEX_HOME="/mnt/c/Users/VICTORIA UNIVERSITY/.codex"
```

Verify the configuration one more time:

```bash
/usr/bin/python3 ./bin/proxy-config --mode check
```

Confirm that the provider is AgentRouter.

---

### 15. Start the installation

Run:

```bash
bash ./installer/setup.sh
```

The installer will perform several operations.

#### Step 1: Configuration preview

It displays the configuration file, selected provider, current URL and target URL.

#### Step 2: Verify project files

It checks the shipped files.

Expected:

```text
OK: 27 shipped files exist and are tracked.
```

#### Step 3: Download the pinned upstream proxy

The installer downloads the specified upstream Git repository and checks out a particular commit.

It also verifies the SHA-256 checksum of the downloaded Python file.

This ensures that the installed file matches the version expected by the setup package.

#### Step 4: Review the downloaded Python script

The installer displays the complete upstream script.

Read the script before approving installation.

The proxy is designed to:

- Receive Codex HTTP requests.
- Inspect Responses API request bodies.
- Remove selected server-specific conversation state.
- Forward the remaining request to AgentRouter.
- Return the upstream response to Codex.
- Record request status and stripping counts in a log.

The sanitizer removes:

- Top-level `previous_response_id`.
- Input item `id` fields.
- Input item fields whose names start with `encrypted`.

The intention is to prevent resource-specific Azure state from being replayed across different upstream resources.

The proxy preserves other request content, including ordinary message content and tool information.

There is a trade-off: removing this state means the model cannot continue using the same hidden server-side reasoning state across turns. It must reason again, although the conversation messages and tool interactions remain available.

Request dumping is disabled by default in the installed service.

#### Step 5: Approve installation

After displaying the script, the installer asks:

```text
Continue with this reviewed script? [y/N]
```

Only approve after reviewing the displayed source and verifying that it matches the expected project.

Enter:

```text
y
```

Press Enter.

#### Step 6: Service installation

The installer:

1. Installs the proxy under your Ubuntu user's local application directory.
2. Creates the systemd user service.
3. Reloads systemd.
4. Enables the service.
5. Starts the service.
6. Waits for the proxy to become available.

#### Step 7: Forwarding verification

The installer sends the direct and proxied unauthenticated requests.

Expected:

```text
Unauthenticated direct=401 proxy=401
```

#### Step 8: Configuration update

After the forwarding test succeeds, the installer updates the selected provider URL in your existing Windows Codex configuration.

The original URL:

```toml
base_url = "https://agentrouter.org/v1"
```

becomes:

```toml
base_url = "http://127.0.0.1:8899/v1"
```

The installer changes only the selected provider URL.

It also creates a backup of the original configuration.

For this installation, the backup was:

```text
C:\Users\VICTORIA UNIVERSITY\.codex\config.toml.bak.strip-proxy.20261117T070318.349993Z
```

#### Step 9: Final local verification

The installer runs its final verification script.

Our installation returned:

```json
{
  "result": "PASS: local checks only",
  "sanitizer_checks": "passed",
  "service": {
    "ActiveState": "active",
    "SubState": "running",
    "UnitFileState": "enabled"
  },
  "listener": "127.0.0.1:8899",
  "request_dumping_disabled": true
}
```

The final configuration check confirmed:

```json
{
  "provider": "AgentRouter",
  "base_url": "http://127.0.0.1:8899/v1"
}
```

At this point, installation is complete.

However, installation verification and authenticated desktop conversation verification are different things. We must still test the actual desktop application.

---

## PART EIGHT: TESTING WINDOWS-TO-UBUNTU CONNECTIVITY

### 16. Verify the proxy service inside Ubuntu

Open Ubuntu.

Run:

```bash
systemctl --user status codex-strip-proxy --no-pager
```

You should see:

```text
Active: active (running)
```

You should also see that the service is enabled.

#### Check the listening port

Run:

```bash
ss -ltnp 'sport = :8899'
```

The proxy should listen on:

```text
127.0.0.1:8899
```

This is important because the proxy should only listen on the local loopback interface.

It should not be exposed directly to your wider network.

---

### 17. Test connectivity from Windows

Now we need to establish that Windows can communicate with the Ubuntu proxy.

Open Windows PowerShell.

You do not need Administrator privileges for this test.

Run:

```powershell
curl.exe --silent --show-error --include --noproxy "*" --connect-timeout 10 --max-time 45 -H "Content-Type: application/json" --data "{}" http://127.0.0.1:8899/v1/responses
```

Expected result:

```text
HTTP/1.1 401 Unauthorized
```

You may also see:

```json
{
  "error": {
    "message": "unauthorized client detected"
  },
  "message": "UNAUTHENTICATED",
  "success": false
}
```

This is not an installation failure.

The test deliberately sends no API key.

The important part is that Windows receives a response from the Ubuntu proxy.

Our actual result:

```text
HTTP/1.1 401 Unauthorized
Server: BaseHTTP/0.6 Python/3.14.4
```

This confirmed that Windows could successfully communicate with the Ubuntu proxy through localhost.

---

## PART NINE: TESTING THE CHATGPT DESKTOP APPLICATION

### 18. Restart the ChatGPT desktop application

After installation, the application needs to reload the updated configuration.

1. Save any active conversations.
2. Open the ChatGPT desktop application.
3. Use its Quit option to exit completely.
4. Do not simply close the window if the application remains running in the background.
5. Reopen ChatGPT.
6. Open Codex.

The application should now use the local proxy URL:

```text
http://127.0.0.1:8899/v1
```

The Windows application communicates with the proxy through WSL2 localhost forwarding.

---

### 19. Create a test directory inside Ubuntu

We need a simple test to establish that Codex can execute shell commands and maintain a conversation across multiple prompts.

Inside Ubuntu, run:

```bash
mkdir -p ~/codex-strip-proxy-test
```

This creates a directory named:

```text
codex-strip-proxy-test
```

inside your Ubuntu home directory.

Its full path is:

```text
/home/victoria_university/codex-strip-proxy-test
```

#### Create the small file

Run:

```bash
head -c 17 /dev/zero | tr '\0' x > ~/codex-strip-proxy-test/small.txt
```

This creates a file containing 17 bytes.

#### Create the medium file

Run:

```bash
head -c 1024 /dev/zero | tr '\0' x > ~/codex-strip-proxy-test/medium.txt
```

This creates a file containing 1,024 bytes.

#### Create the large file

Run:

```bash
head -c 4096 /dev/zero | tr '\0' x > ~/codex-strip-proxy-test/large.txt
```

This creates a file containing 4,096 bytes.

You can verify the files yourself:

```bash
ls -l ~/codex-strip-proxy-test
```

Or use:

```bash
wc -c ~/codex-strip-proxy-test/*
```

Expected sizes:

| File       | Size        |
| ---------- | ----------- |
| small.txt  | 17 bytes    |
| medium.txt | 1,024 bytes |
| large.txt  | 4,096 bytes |

---

### 20. Open the Ubuntu test directory in Windows

Because the ChatGPT desktop application is installed on Windows, we need to open the Ubuntu directory through the WSL filesystem.

Open Windows PowerShell.

Run:

```powershell
explorer.exe "\\wsl.localhost\Ubuntu\home\victoria_university\codex-strip-proxy-test"
```

Windows Explorer will open the Ubuntu directory.

In the ChatGPT desktop application's Codex interface:

1. Select the option to open a folder.
2. Choose the `codex-strip-proxy-test` folder.
3. Confirm that the folder is the active workspace.

> **Important:** During our first attempt, Codex was still working inside:
>
> ```text
> C:\Users\VICTORIA UNIVERSITY\Documents
> ```
>
> That was the wrong directory.
>
> The correct directory is:
>
> ```text
> /home/victoria_university/codex-strip-proxy-test
> ```

Always confirm the active workspace before running the test.

---

## PART TEN: TESTING CONVERSATION REPLAY

### 21. Start monitoring the proxy logs

Before sending prompts, open an Ubuntu terminal.

Run:

```bash
tail -n 0 -F "$HOME/.local/state/codex-strip-proxy/proxy.log"
```

This displays new proxy log entries as they arrive.

The command does not stop or restart the proxy.

Keep this terminal open.

To stop monitoring later, press:

```text
Ctrl + C
```

This only stops the log viewer. It does not stop the service.

---

### 22. Send the first Codex prompt

In the ChatGPT desktop application's Codex interface, make sure the correct Ubuntu test directory is open.

Send:

```text
Use a shell tool to list the files in this directory and their byte sizes. Do not modify anything.
```

Codex should execute a shell command and return the three files.

Expected result:

```text
large.txt — 4,096 bytes
medium.txt — 1,024 bytes
small.txt — 17 bytes
```

It should also confirm that no files were modified.

---

### 23. Send the second prompt

In the same Codex conversation, send:

```text
Which of those files is the largest?
```

Expected answer:

```text
large.txt is largest at 4,096 bytes.
```

This second prompt is important because it tests whether Codex can use the context from the earlier tool execution.

A successful result demonstrates that the shell tool and conversation follow-up are working.

#### Actual test results

The installation produced the following results:

First prompt:

```text
- large.txt — 4,096 bytes
- medium.txt — 1,024 bytes
- small.txt — 17 bytes

No files were modified.
```

Second prompt:

```text
large.txt is largest at 4,096 bytes.
```

Both prompts completed successfully.

---

## PART ELEVEN: VERIFYING THE PROXY LOGS

### 24. Inspect the proxy logs

Return to Ubuntu.

Run:

```bash
tail -n 20 ~/.local/state/codex-strip-proxy/proxy.log
```

You should see entries similar to:

```text
2026-11-17 10:12:43 /v1/responses http=200 stripped=13 req=119096B
2026-11-17 10:12:50 /v1/responses http=200 stripped=18 req=123440B
2026-11-17 10:12:56 /v1/responses http=200 stripped=22 req=126252B
2026-11-17 10:13:04 /v1/responses http=200 stripped=26 req=131319B
2026-11-17 10:13:15 /v1/responses http=200 stripped=31 req=179509B
2026-11-17 10:13:26 /v1/responses http=200 stripped=36 req=186898B
2026-11-17 10:13:33 /v1/responses http=200 stripped=40 req=190478B
2026-11-17 10:13:40 /v1/responses http=200 stripped=5 req=48709B
2026-11-17 10:13:46 /v1/responses http=200 stripped=44 req=195047B
2026-11-17 10:14:05 /v1/responses http=200 stripped=48 req=197300B
```

Your actual timestamps and request sizes will differ.

#### What do the log entries mean?

For example:

```text
http=200 stripped=48 req=197300B
```

This means:

- **http=200:** The upstream request completed successfully.
- **stripped=48:** The sanitizer removed 48 matching state fields in that request.
- **req=197300B:** The original request body was 197,300 bytes.

The stripping count is cumulative for matching fields in that individual request. It does not mean 48 separate messages were removed.

#### Understanding HTTP 401

During the earlier forwarding test, you saw:

```text
http=401 stripped=0
```

This was expected because the request contained no API key.

#### Understanding HTTP 503

During authenticated Codex activity, some requests returned:

```text
http=503 stripped=7
```

This indicates that the upstream service returned HTTP 503 for those requests.

There were also successful HTTP 200 responses afterward.

Therefore, intermittent upstream failures were observed, even though the actual test prompts completed successfully.

Do not treat HTTP 503 as a successful request. Continue monitoring if these errors persist.

#### Actual verification results

The logs confirmed:

- Successful HTTP 200 responses.
- Positive stripping counts.
- Large Responses API request bodies.
- Successful authenticated Codex activity.

This is important evidence that the proxy was actively processing real Codex requests rather than simply running without being used.

---

## PART TWELVE: FINAL VERIFICATION AND TROUBLESHOOTING

### 25. Verify the service whenever needed

If you want to check whether the proxy is running, use:

```bash
systemctl --user status codex-strip-proxy --no-pager
```

To restart the service:

```bash
systemctl --user restart codex-strip-proxy
```

To stop it:

```bash
systemctl --user stop codex-strip-proxy
```

To start it again:

```bash
systemctl --user start codex-strip-proxy
```

To check its listening port:

```bash
ss -ltnp 'sport = :8899'
```

The expected address is:

```text
127.0.0.1:8899
```

---

### 26. Common problems and their solutions

#### Problem 1: WSL says there are no installed distributions

Example:

```text
Windows Subsystem for Linux has no installed distributions.
```

**Solution:**

Open PowerShell as Administrator and run:

```powershell
wsl --install -d Ubuntu
```

Complete the Ubuntu setup before running Linux commands.

---

#### Problem 2: Ubuntu asks for a password

This is normal.

The Ubuntu password is independent of your Windows password.

Type your chosen Linux password even though the terminal does not display the characters.

---

#### Problem 3: systemctl reports that systemd is not running

Check:

```bash
cat /etc/wsl.conf
```

Make sure it contains:

```ini
[boot]
systemd=true
```

Then, from PowerShell:

```powershell
wsl --shutdown
```

Reopen Ubuntu and try again.

---

#### Problem 4: Verification script reports an invalid pipefail option

Example:

```text
invalid option nameine 5: set: pipefail
```

This occurred when the repository was initially cloned under the Windows-mounted filesystem.

**Solution:**

Clone the repository inside Ubuntu:

```bash
cd ~
git clone https://github.com/mugabiBenjamin/codex-strip-proxy-setup.git
cd codex-strip-proxy-setup
```

Then repeat the verification.

---

#### Problem 5: Proxy configuration says config.toml does not exist

Example:

```text
STOP: Config must be an existing regular file, not a symlink.
```

This can happen when the Codex desktop application is installed on Windows but the setup script is running inside Ubuntu.

Set the correct configuration directory:

```bash
export CODEX_HOME="/mnt/c/Users/VICTORIA UNIVERSITY/.codex"
```

Then verify:

```bash
echo "$CODEX_HOME"
```

Run:

```bash
/usr/bin/python3 ./bin/proxy-config --mode check
```

---

#### Problem 6: Windows cannot connect to the proxy

Check the service inside Ubuntu:

```bash
systemctl --user status codex-strip-proxy --no-pager
```

Check the port:

```bash
ss -ltnp 'sport = :8899'
```

Then repeat the Windows PowerShell test:

```powershell
curl.exe --silent --show-error --include --noproxy "*" --connect-timeout 10 --max-time 45 -H "Content-Type: application/json" --data "{}" http://127.0.0.1:8899/v1/responses
```

A 401 response is expected.

---

#### Problem 7: Codex uses the wrong directory

Confirm the workspace folder in the Codex application.

For this test, use:

```text
/home/victoria_university/codex-strip-proxy-test
```

You can reopen it through Windows Explorer:

```powershell
explorer.exe "\\wsl.localhost\Ubuntu\home\victoria_university\codex-strip-proxy-test"
```

---

#### Problem 8: Codex returns intermittent HTTP 503 errors

Check:

```bash
tail -n 30 ~/.local/state/codex-strip-proxy/proxy.log
```

Look for successful HTTP 200 entries and repeated HTTP 503 responses.

The proxy can be functioning correctly while the upstream provider experiences intermittent failures.

Do not assume that every HTTP 503 is caused by WSL or the local proxy.

---

## PART THIRTEEN: COMPLETING THE FINAL DESKTOP RESTART TEST

### 27. Why a complete restart matters

The project defines completion as a successful authenticated Codex conversation replay after restarting the desktop application.

This is different from simply closing and reopening a conversation.

We need to confirm that the application reloads the updated provider URL and continues using the local proxy.

#### Step 1: Save your work

Save active conversations and finish any running tasks.

#### Step 2: Completely quit ChatGPT

Use the application's Quit action.

Do not assume that closing the window completely exits the application.

#### Step 3: Reopen ChatGPT

Launch ChatGPT again from the Windows Start menu.

Open Codex.

#### Step 4: Confirm the configuration

In Ubuntu, make sure `CODEX_HOME` is set:

```bash
export CODEX_HOME="/mnt/c/Users/VICTORIA UNIVERSITY/.codex"
```

Run:

```bash
/usr/bin/python3 ./bin/proxy-config --mode check
```

The expected current and target URLs should both be:

```text
http://127.0.0.1:8899/v1
```

#### Step 5: Start monitoring new log entries

Run:

```bash
date -Is
```

Then:

```bash
tail -n 0 -F "$HOME/.local/state/codex-strip-proxy/proxy.log"
```

#### Step 6: Open the Ubuntu test directory

In PowerShell:

```powershell
explorer.exe "\\wsl.localhost\Ubuntu\home\victoria_university\codex-strip-proxy-test"
```

Open that folder in Codex.

#### Step 7: Repeat the two prompts

First:

```text
Use a shell tool to list the files in this directory and their byte sizes. Do not modify anything.
```

Second:

```text
Which of those files is the largest?
```

Expected answer:

```text
large.txt — 4,096 bytes
```

#### Step 8: Confirm the logs

The new log entries should show successful HTTP 200 requests and positive stripping counts where applicable.

The tool execution and follow-up answer must both be correct.

The final test must also complete without the Azure cross-resource errors that the proxy is intended to address.

---

## PART FOURTEEN: FINAL COMPLETION CHECKLIST

### 28. Installation verification checklist

Use this checklist to assess whether the setup is complete.

#### Windows configuration

- [ ] AgentRouter API key stored as a Windows user environment variable.
- [ ] Codex configured to use AgentRouter.
- [ ] Existing Windows Codex configuration preserved.
- [ ] Provider URL updated to the local proxy.

#### WSL2 and Ubuntu

- [ ] WSL2 installed.
- [ ] Ubuntu installed.
- [ ] Ubuntu Linux user created.
- [ ] systemd enabled.
- [ ] systemd verified as running.
- [ ] Git installed.
- [ ] Python installed.
- [ ] Curl installed.
- [ ] iproute2 installed.

#### Repository

- [ ] Repository cloned into Ubuntu's Linux filesystem.
- [ ] Main branch checked out.
- [ ] 27 shipped files verified.
- [ ] 39 unit tests executed successfully.
- [ ] One test skipped, with no failed tests.

#### Proxy installation

- [ ] Pinned upstream source downloaded.
- [ ] SHA-256 checksum verified.
- [ ] Proxy service installed.
- [ ] systemd service enabled.
- [ ] systemd service running.
- [ ] Proxy listening on `127.0.0.1:8899`.
- [ ] Request dumping disabled.
- [ ] Forwarding probe returned the expected 401.
- [ ] Existing Windows Codex configuration updated.
- [ ] Original configuration backup created.
- [ ] Sanitizer checks passed.

#### Connectivity and functional testing

- [ ] Windows PowerShell successfully reached the Ubuntu proxy.
- [ ] Authenticated Codex requests reached the proxy.
- [ ] Successful HTTP 200 responses observed.
- [ ] Positive stripping counts observed.
- [ ] Ubuntu test directory created.
- [ ] Three test files created with the correct sizes.
- [ ] Codex successfully executed the shell tool.
- [ ] Codex correctly listed the files.
- [ ] Codex correctly identified the largest file.
- [ ] Conversation follow-up completed successfully.
- [ ] No files were modified during the test.

#### Final restart verification

- [ ] Completely quit the ChatGPT desktop application.
- [ ] Reopened the application.
- [ ] Confirmed the local provider URL persisted.
- [ ] Successfully repeated both authenticated prompts after restarting.
- [ ] Confirmed fresh HTTP 200 logs after the restart.
- [ ] Confirmed correct tool results and no Azure resource error.

---

### 29. Final conclusion

The installation process successfully established a working connection between the Windows ChatGPT desktop application and a proxy running inside Ubuntu under WSL2.

The proxy was installed using a pinned upstream version and verified using its SHA-256 checksum.

The systemd service was successfully enabled and started, listening only on the local loopback address:

```text
127.0.0.1:8899
```

The existing Windows Codex configuration was preserved, backed up and updated to route AgentRouter requests through the local proxy.

The Windows-to-Ubuntu connectivity test returned the expected HTTP 401 response.

More importantly, actual authenticated Codex requests were observed in the proxy logs. Successful HTTP 200 responses and positive stripping counts confirmed that the sanitizer was actively processing requests.

The functional test also succeeded:

- Codex listed three files in the Ubuntu test directory.
- The reported file sizes were correct.
- Codex correctly identified `large.txt` as the largest file at 4,096 bytes.
- The follow-up prompt completed successfully in the same conversation.

Installation and functional testing have therefore succeeded.

The remaining formal completion requirement is to perform a full desktop application restart and repeat the authenticated conversation test afterward.

Once that final test passes, the setup meets the project's stated completion criteria.

---

> **Important maintenance notes**
>
> - Keep your AgentRouter API key private.
> - Do not delete the original Codex configuration backup.
> - Keep the proxy repository and installed service files intact.
> - Start Ubuntu and ensure the user service is running before using Codex if WSL has been shut down.
> - Monitor repeated HTTP 503 errors if they continue.
> - Do not expose the proxy on a public network interface.
> - If you change the proxy port, update the installer and verification commands consistently.
> - If you change the Windows Codex configuration location, update `CODEX_HOME` accordingly.

---

### Final architecture

```text
Windows 11
    |
    |-- ChatGPT Desktop Application
    |
    |-- Codex configuration
    |       |
    |       |-- Provider: AgentRouter
    |       |
    |       |-- API key: CODEX_GATEWAY_API_KEY
    |       |
    |       |-- Base URL: http://127.0.0.1:8899/v1
    |
    |-- WSL2
            |
            |-- Ubuntu
                    |
                    |-- systemd user service
                    |
                    |-- codex-strip-proxy
                    |
                    |-- 127.0.0.1:8899
                            |
                            |-- Request sanitization
                            |
                            |-- AgentRouter
                                    |
                                    |-- Authenticated API requests
                                    |
                                    |-- Model responses
```

---

*End of guide.*
