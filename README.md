A notification daemon for [Omarchy](https://omarchy.org). It replaces the
built-in notification service with a stacking deck that groups by source,
reads what a notification is actually offering you, and lets you act on it
without leaving the card.

<img src="assets/deck.gif" width="440" alt="Notifications landing and stacking in the corner of the screen">

## What it does

**Stacks and groups.** Notifications from the same source collect into one
deck. Hovering expands it. Nothing is hidden behind a "3 more" summary —
every notification is a real card you can act on.

**Reads the contents.** A verification code, a link or a phone number in the
body becomes a labelled button: `Copy code`, `Open link`, `Copy number`. A mark
on the headline tells you a card is
carrying something before you hover, because the useful part of a message is
usually past the ellipsis.

<img src="assets/actions.png" width="369" alt="A card showing a Copy code button">

A message carrying two codes gets a button each, labelled with the digits,
because "Copy code" twice is a coin toss. Detection is deliberately
conservative: `412 passed, 0 failed` is not a code, and neither is
`Claude Code build 1841`.

**Shows the sender's own actions.** The freedesktop spec has carried actions
all along; most desktops draw none of them. Reply, Mark as read, whatever the
app offered, appear as buttons on hover.

**Replies to your phone.** Phone notifications reach the desktop through KDE
Connect, and the ones carrying a reply channel grow a text field on the card.
The answer goes back to the conversation, and the notification is dismissed on
the phone too. Nothing new lands and nothing expires while you are typing, so
the field cannot move out from under you mid-sentence.

<img src="assets/reply.png" width="369" alt="Typing a reply into a notification">

**Sends you back where it came from.** Clicking a card focuses the window that
source is already showing in — a Slack notification lands in the Chrome you
already have Slack open in, rather than a new tab — and opens something new
only when there is nothing to go back to. It can only see the tab a browser is
actually showing, so a site sitting in a background tab opens fresh.

**Quietens one source at a time.** Right-click a card and pick how long. It is
the *source* that goes quiet, not the app that relayed it: snoozing a Slack
notification that arrived through Chrome silences `app.slack.com` and nothing
else, and snoozing a noisy shopping app on your phone leaves WhatsApp alone.
Snoozed notifications are still recorded — they go to history without ever
being on screen.

The panel does the same for everything at once. Both offer the lengths in
`snoozeDurations`, which are yours to change.

**Lets the code through anyway.** A snooze or a silence holds everything back
except a notification carrying a verification code. You asked for that code
thirty seconds ago and it expires in five minutes — and being locked out of a
login because you had quietened Slack is exactly the failure that makes people
stop snoozing anything. The key beside the panel's snooze button closes the
hole for the times you want nothing at all. Copying a code dismisses its
notification; there is nothing left in it afterwards.

**Shows you what quiet cost.** Silence is only tolerable if you can see what it
kept from you. While anything is being held back, the panel lists the sources
that caught something and opens each one to show what it caught, newest first —
capped at both ends, so a fortnight of silence doesn't turn a panel into a log
file.

<img src="assets/quiet.png" width="404" alt="The bar indicator and the panel behind it">

**Resolves real icons.** Your own icon themes win; web notifications fall back
to the site's own icon, in dark and light variants to suit the theme.

## Fork Notice

This is a security-hardened fork of [njpatel/omapager](https://github.com/njpatel/omapager) by Neil Patel.
The original project was renamed from "Omapager" to "Omaping" and reorganized with a modular structure.

Key changes from upstream:
- Default `fetchIcons: false` (opt-in network requests)
- Input sanitization for all IPC and CLI arguments
- Exact-match only for KDE Connect reply channels (prevents spoofing)
- Redirect limits and punycode decoding for icon fetcher (prevents SSRF/homograph)
- History files stored with 0600 permissions, sensitive fields excluded
- Max notification cap (100) to prevent DoS
- Rate limiting on IPC endpoints
- Modular `src/` layout with proper Python package

See [CHANGELOG.md](CHANGELOG.md) for full details.

## Install

```bash
git clone https://github.com/FrancKINANI/notif-oma.git \
  ~/.config/omarchy/plugins/franckinani.omaping
```

Then in `~/.config/omarchy/shell.json`, turn off the built-in service, add the
plugin, and put the indicator in the bar beside the other status glyphs, since
it behaves like one:

```json
{
  "disabledPlugins": ["omarchy.notifications"],
  "plugins": [{ "id": "franckinani.omaping" }],
  "bar": { "layout": { "center": ["omarchy.indicators", "franckinani.omaping", "omarchy.clock"] } }
}
```

`omarchy-restart-shell` to pick it up. (Not `omarchy-refresh-shell` — that
resets `shell.json` to defaults.)

### Removing it

```bash
omarchy plugin remove franckinani.omaping
```

Then undo the three lines above: take `omarchy.notifications` back out of
`disabledPlugins` so the built-in service can claim the bus again, and drop
`franckinani.omaping` from the bar layout. `omarchy-restart-shell` to apply.

State is left behind on purpose, in case you are only reinstalling —
`rm -rf ~/.local/state/omarchy/omaping` clears the history and the resolved
icons for good.

## Settings

| key | default | what it does |
| --- | --- | --- |
| `stacking` | `source` | `source` gives each sender its own deck; `all` puts everything in one |
| `actionsAlign` | `right` | which end of a card its buttons sit at |
| `hideSettingsAction` | `true` | drop the browser's "Settings" button, which is on every web notification and is never the one you wanted |
| `snoozeDurations` | `30, 60, 240, tomorrow` | what the snooze menus offer — minutes, or `tomorrow` |
| `wakeHour` | `8` | the hour "until tomorrow" wakes a source at |
| `smartRaise` | `true` | match a site against browser window titles, so a click lands in the window already showing it |
| `alwaysShow` | `false` | keep the bar slot even when nothing is held back, so the centre of the bar never shifts |
| `codesBypassQuiet` | `true` | let a notification carrying a verification code through a snooze or a silence |
| `timeFormat` | `system` | `system` follows `LC_TIME`; `24h` and `12h` pin it |
| `sourceLimit` | `8` | how many quietened sources the panel lists |
| `heldPerSource` | `10` | how many held notifications it shows per source |

Every history entry is the text of a message somebody sent you, so it is
trimmed by age as well as count: **7 days or 200 entries**, whichever comes
first. Resolved icons are dropped after 60 days unused, and nothing is ever
written to the system log.

Settings live on the bar widget's entry in `shell.json`, all in one place
next to `id`:

```json
{ "id": "franckinani.omaping", "snoozeDurations": ["60", "480"], "wakeHour": 9 }
```

## The bar

omaping takes a slot in the bar only while it is keeping something from you,
and nothing at all the rest of the time. Hovering the centre of the bar reveals
it, the way Omarchy reveals its own inactive indicators — that is the way back
into silence when nothing is showing.

| | |
| --- | --- |
| crossed-out bell, in the theme's urgent colour | silenced |
| bell with a `z` in it, in amber | snoozed — everything, or a source |
| crossed-out bell, dimmed | nothing held back |

Same crossed-out bell as Omarchy's own indicator, so a silenced desktop looks
the same whichever service is running. Amber rather than red for a snooze,
because a snooze ends by itself.

**Left-click** silences and unsilences. **Right-click** opens the panel: the
switch, a button beside it that snoozes everything for a while, and the list of
what is being kept from you — when each source comes back, how much it has
caught, and the messages themselves when you open one.

## Keybindings

Omarchy's five stock bindings on the comma key keep working unchanged.
omaping answers the same IPC target the built-in service did, so there is
nothing to rebind and nothing to configure:

| | |
| --- | --- |
| `SUPER` `,` | dismiss the newest notification |
| `SUPER` `SHIFT` `,` | dismiss all of them |
| `SUPER` `CTRL` `,` | toggle silencing |
| `SUPER` `ALT` `,` | invoke the newest one, as clicking it would |
| `SUPER` `SHIFT` `ALT` `,` | put the last few back on screen |

### Worth adding

Three things the stock bindings have no key for. All three are free on a stock
install — check yours with `omarchy menu keybindings --print`, and `hl.unbind`
first if you have moved things around.

In `~/.config/hypr/bindings.lua`:

```lua
-- Copy a code without touching the mouse. The notification takes itself away.
o.bind("SUPER + ALT + C", "Copy code from newest notification",
       "omarchy-shell omaping offer code")

-- Next to SUPER + CTRL + comma, which silences. Quiet for an hour, rather
-- than quiet until you remember you turned it off.
o.bind("SUPER + CTRL + ALT + comma", "Snooze all notifications for an hour",
       "omarchy-shell omaping snoozeAll 60")

-- What is snoozed, what it has held, and the way back. Worth a key: the bar
-- icon is not there at all when nothing is being held back.
o.bind("SUPER + CTRL + SHIFT + comma", "Notification options",
       "omarchy-shell omaping.panel toggle")
```

## Driving it from a script

```
omarchy-shell omaping count            how many are on screen
omarchy-shell omaping clear            dismiss them
omarchy-shell omaping dnd              toggle Do Not Disturb
omarchy-shell omaping expand           open the deck, as hovering would
omarchy-shell omaping offer code       take the front card's offer (code|link|phone)
omarchy-shell omaping act reply        invoke one of the sender's actions
omarchy-shell omaping reply "text"     answer the front card ("" opens the field)
omarchy-shell omaping snooze 60        quieten the front card's source, in minutes
omarchy-shell omaping snoozeAll 60     quieten everything for 60 minutes, or wake it
omarchy-shell omaping codes off        stop letting verification codes through
omarchy-shell omaping unsnooze ""      wake everything ("" for all, or a source key)
omarchy-shell omaping snoozes          what is snoozed, and until when
omarchy-shell omaping stack source     switch stacking mode
omarchy-shell omaping align right      switch which end the buttons sit at
omarchy-shell omaping probe            what the daemon believes, as JSON

omarchy-shell omaping.panel toggle     the panel
omarchy-shell omaping.panel expand x   open a source's held list, as clicking it would
```

## Seeing it work

```bash
omaping-demo                       # the everyday scenes
omaping-demo --scene interactive   # codes, links, and the sender's buttons
omaping-demo --scene routing       # where a click sends you, per source
omaping-demo --scene reply         # inline reply, against a stand-in phone
omaping-demo --replay 40           # your own notifications, re-sent
omaping-demo --list
```

`--scene routing` reads your open windows and prints what each card *should*
do before it sends anything, so you can check it against what happens.
`--scene reply` writes a fixture the daemon treats as a repliable notification
and logs the reply to a file rather than sending it to a person.

## Requirements

Omarchy (Quickshell 0.3.x, Hyprland), and Python 3 for the helpers.

Two more things are worth having, and they are not the same kind of thing.

**`wl-clipboard` — recommended.** Not an Omarchy dependency, so check before you
assume it: `command -v wl-copy`. The copy buttons work either way, but with it a
copied verification code is marked sensitive and Omarchy's clipboard history
skips it. Either way the code is cleared again 90 seconds later, unless you have
copied something else since — that stays.

**KDE Connect — the whole phone half.** Without it there are no phone
notifications at all: it is the bridge that puts them on the bus in the first
place, so the reply field, `Mark as read` and the grouping by the app a message
really came from all go with it.

```bash
sudo pacman -S wl-clipboard kdeconnect   # kdeconnect also needs the phone app
```

## Licence

Apache-2.0.

## Development

### Project Structure

```
omaping/
├── src/
│   ├── qml/
│   │   ├── components/     # Toast.qml, DeedButton.qml
│   │   ├── widgets/        # Widget.qml (bar widget + panel)
│   │   └── services/       # Service.qml (notification daemon)
│   ├── js/
│   │   └── core/           # Detect.js, Layout.js, Markup.js, Store.js
│   └── python/
│       ├── omaping/        # Python package (store, icon, kdeconnect, demo)
│       └── scripts/        # Entry points (omaping-store, omaping-icon, etc.)
├── tests/
├── packaging/
├── pyproject.toml          # Python package config
├── package.json            # JS tooling (prettier)
├── .editorconfig
└── .prettierrc
```

### Running Tests

```bash
# Python tests
pip install -e ".[dev]"
pytest tests/python/

# Format code
npm install
npm run format
```

### Building the Plugin

The plugin is installed directly from the repository. Omarchy loads the QML entry points from `manifest.json`.