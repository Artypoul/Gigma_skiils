# Playwright CLI Workflows

Use the wrapper script and snapshot often.
Assume `PWCLI` points to the bundled wrapper script. Invoke it directly as `"$PWCLI"`; do not create an alias.
In this repo, run commands from `output/playwright/<label>/` to keep artifacts contained.

## Standard interaction loop

```bash
"$PWCLI" open https://example.com
"$PWCLI" snapshot
"$PWCLI" click e3
"$PWCLI" snapshot
```

## Form submission

```bash
"$PWCLI" open https://example.com/form --headed
"$PWCLI" snapshot
"$PWCLI" fill e1 "user@example.com"
"$PWCLI" fill e2 "password123"
"$PWCLI" click e3
"$PWCLI" snapshot
"$PWCLI" screenshot
```

## Data extraction

```bash
"$PWCLI" open https://example.com
"$PWCLI" snapshot
"$PWCLI" eval "document.title"
"$PWCLI" eval "el => el.textContent" e12
```

## Debugging and inspection

Capture console messages and network activity after reproducing an issue:

```bash
"$PWCLI" console warning
"$PWCLI" network
```

Record a trace around a suspicious flow:

```bash
"$PWCLI" tracing-start
# reproduce the issue
"$PWCLI" tracing-stop
"$PWCLI" screenshot
```

## Sessions

Use sessions to isolate work across projects:

```bash
"$PWCLI" -s=marketing open https://example.com
"$PWCLI" -s=marketing snapshot
"$PWCLI" -s=checkout open https://example.com/checkout
```

Or set the session once:

```bash
export PLAYWRIGHT_CLI_SESSION=checkout
"$PWCLI" open https://example.com/checkout
```

## Configuration file

By default, the CLI reads `playwright-cli.json` from the current directory. Use `--config` to point at a specific file.

Minimal example:

```json
{
  "browser": {
    "launchOptions": {
      "headless": false
    },
    "contextOptions": {
      "viewport": { "width": 1280, "height": 720 }
    }
  }
}
```

## Troubleshooting

- If an element ref fails, run `"$PWCLI" snapshot` again and retry.
- If the page looks wrong, re-open with `--headed` and resize the window.
- If a flow depends on prior state, use a named `-s=name` session.
