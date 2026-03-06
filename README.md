## High-Risk Command Approval Rule

  Before executing any shell command in a risky category, stop and ask me
  first.
  Do not run it until I explicitly approve that exact action.

  Treat the following as risky and requiring prior approval:

  1. Process, service, session, host, or environment discovery:
     - Examples: `wmic`, `tasklist`, `Get-Process`, `Get-CimInstance`, `Get-
  WmiObject`, `query`, `whoami`, `systeminfo`, `netstat`, registry queries,
  environment dumps.

  2. PowerShell commands beyond simple local file reads:
     - Especially anything using `-ExecutionPolicy`, `Bypass`,
  `EncodedCommand`, `Invoke-Expression`, `iex`, `Invoke-WebRequest`, `iwr`,
  `Invoke-RestMethod`, `irm`, hidden window flags, or nested shell launch.

  3. Any outbound network request or remote content fetch:
     - Examples: `curl`, `wget`, `Invoke-WebRequest`, `Invoke-RestMethod`,
  package/bootstrap installers, or any command containing `http://` or
  `https://`.
     - Always ask first if the command includes tokens, API keys, bearer
  headers, cookies, auth headers, or webhook URLs.

  4. Any command that downloads and then executes code, scripts, or
  installers.

  5. Any change to security, sandbox, approval, or execution settings:
     - Examples: execution policy, Defender, firewall, certificates, PATH,
  startup items, scheduled tasks, services, registry autoruns, sandbox
  config, approval bypass.

  6. Any command that may expose secrets or credential-bearing files:
     - Examples: SSH keys, tokens, auth config, `.env`, browser/session
  secrets, cloud credentials.

  7. Any command outside the current workspace that touches user-profile,
  system, or admin-controlled areas, unless I explicitly asked for it.

  8. Any elevation, bypass, or stealth behavior:
     - Examples: admin/elevated execution, `runas`, `sudo`, WSL setup,
  sandbox bypass, approval bypass, hidden/background shell chains.

  Approval behavior:
  - Ask before running.
  - Show a short reason and the exact command you want to run.
  - Wait for my reply.
  - If I do not clearly approve, do not run it.
  - Do not rephrase the same risky action as a different command to avoid
  asking.

  Safe-by-default behavior:
  - Normal repo reads, searches, edits, diffs, and local builds/tests are
  fine without asking.
  - `bash` and `cmd` are allowed by themselves.
  - Approval is required for the risky payload inside them, not for the
  shell name alone.

  Hard bans unless I explicitly approve:
  - `wmic`
  - `powershell -ExecutionPolicy Bypass`
  - `iex`
  - `irm`
  - remote bootstrap scripts
  - authenticated `curl` or similar outbound requests with secrets
