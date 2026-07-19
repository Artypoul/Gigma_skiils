# Playwright CLI Reference

Use the wrapper script unless the CLI is already installed globally:

```bash
export PLAYWRIGHT_SKILL_ROOT="<absolute path to the loaded playwright skill directory>"
export PWCLI="$PLAYWRIGHT_SKILL_ROOT/scripts/playwright_cli.sh"
"$PWCLI" --help
```

Resolve `PLAYWRIGHT_SKILL_ROOT` from the location of the loaded `SKILL.md`; do not assume a user-scoped install path.

## Core

```bash
"$PWCLI" open https://example.com
"$PWCLI" close
"$PWCLI" snapshot
"$PWCLI" click e3
"$PWCLI" dblclick e7
"$PWCLI" type "search terms"
"$PWCLI" press Enter
"$PWCLI" fill e5 "user@example.com"
"$PWCLI" drag e2 e8
"$PWCLI" hover e4
"$PWCLI" select e9 "option-value"
"$PWCLI" upload ./document.pdf
"$PWCLI" check e12
"$PWCLI" uncheck e12
"$PWCLI" eval "document.title"
"$PWCLI" eval "el => el.textContent" e5
"$PWCLI" dialog-accept
"$PWCLI" dialog-accept "confirmation text"
"$PWCLI" dialog-dismiss
"$PWCLI" resize 1920 1080
```

## Navigation

```bash
"$PWCLI" go-back
"$PWCLI" go-forward
"$PWCLI" reload
```

## Keyboard

```bash
"$PWCLI" press Enter
"$PWCLI" press ArrowDown
"$PWCLI" keydown Shift
"$PWCLI" keyup Shift
```

## Mouse

```bash
"$PWCLI" mousemove 150 300
"$PWCLI" mousedown
"$PWCLI" mousedown right
"$PWCLI" mouseup
"$PWCLI" mouseup right
"$PWCLI" mousewheel 0 100
```

## Save as

```bash
"$PWCLI" screenshot
"$PWCLI" screenshot e5
"$PWCLI" pdf
```

## Tabs

```bash
"$PWCLI" tab-list
"$PWCLI" tab-new
"$PWCLI" tab-new https://example.com/page
"$PWCLI" tab-close
"$PWCLI" tab-close 2
"$PWCLI" tab-select 0
```

## DevTools

```bash
"$PWCLI" console
"$PWCLI" console warning
"$PWCLI" network
"$PWCLI" run-code "await page.waitForTimeout(1000)"
"$PWCLI" tracing-start
"$PWCLI" tracing-stop
```

## Sessions

Use a named session to isolate work:

```bash
"$PWCLI" --session todo open https://demo.playwright.dev/todomvc
"$PWCLI" --session todo snapshot
```

Or set an environment variable once:

```bash
export PLAYWRIGHT_CLI_SESSION=todo
"$PWCLI" open https://demo.playwright.dev/todomvc
```
