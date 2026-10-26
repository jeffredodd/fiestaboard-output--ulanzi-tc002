# AWTRIX NG Output Plugin

Shows your FiestaBoard pages on a **Ulanzi TC002** running
[AWTRIX NG](https://github.com/Blueforcer/awtrix-ng), over your local
network. The board becomes an app in the clock's rotation, beside the
clock's own apps and scripts.

```
HELLO WORLD
SUNNY 72
🟥🟧🟨🟩🟦🟪
```

52 × 16 pixels, 3 rows of 13 characters.

> **Beta.** Output plugins need FiestaBoard 10.0.0 or later, where the
> output-plugin API is still a beta. This plugin is written
> against the AWTRIX NG 1.2.2 documentation and tested against a mock clock.
> It has not been timed on a real TC002 yet; see
> [Verify on your clock](#verify-on-your-clock).

## Requirements

- FiestaBoard 10.0.0 or later (output plugins need no switch turned on)
- A Ulanzi TC002 running AWTRIX NG, on the same network as FiestaBoard
- Nothing to install on the clock, and no cloud service or account

The 32 × 8 AWTRIX NG clocks (TC001, ESP32 builds) are not supported: they
cannot draw the full-size layouts the plugin sends.

## Quick start

1. In FiestaBoard, open **Displays → Marketplace** and paste
   `https://github.com/rummeyer/fiestaboard-output--awtrix-ng` under **Bring
   your own display** (or use **Integrations → Marketplace → Add from Git**).
   Or from a terminal:

   ```sh
   curl -X POST http://<fiestaboard>:4420/api/plugins/install \
     -H "Content-Type: application/json" \
     -d '{"repository": "https://github.com/rummeyer/fiestaboard-output--awtrix-ng"}'
   ```

2. Open **Displays → Add a display** and pick **AWTRIX NG (Ulanzi TC002)**.
3. Enter the clock's address, or press **Find my clock**. A local name such as
   `awtrixng-a1b2c3.local` works too.
4. Press **Test connection**. It answers with the clock's firmware version.
5. Put a page on the board. The clock switches to the new app
   **FiestaBoard** and shows it.

## What it shows

FiestaBoard lays each page out in its 3×5 LED font: **3 rows of 13
characters**.

- Letters, digits and punctuation, white on black; capitals read best at
  this size
- Colour tiles `{63}`–`{68}` as solid cells in the board colours, `{69}` white,
  `{70}`/`{71}` unlit
- Colour spans (`{red:HOT}`), block spans and icons (`{icon:sun}`), exactly as
  the board's preview in FiestaBoard draws them
- Pixel canvases over the text, on a FiestaBoard with canvas pages

### Why 3 rows fit on 16 pixels

Three rows of the 3×5 font with a dark pixel row between them need 17 pixel
rows, and FiestaBoard makes no LED board smaller than 3 × 10 characters. So
FiestaBoard draws the board at 52 × 17, and the plugin leaves out the dark row
between the second and the third text row before it sends a frame:

```
 HELLO WORLD        pixel rows 0 to 4
                    row 5 stays dark
 SUNNY 72           pixel rows 6 to 10
 🟥🟧🟨🟩🟦🟪       pixel rows 11 to 15, right under the second
```

The first row, often a title, keeps its space; the second and third touch.
The board's preview in FiestaBoard still shows the dark row. The larger 5×7
font fits only 2 rows on 16 pixels and is not offered.

## How it behaves on the clock

**An app in the rotation.** Each frame is a pushed app
(`PUT /api/v1/apps/pushed/FiestaBoard`) whose layout covers the whole display
and draws one picture. A layout keeps all 52 × 16 pixels, whatever the clock's
**Enlarge apps** setting says. The app takes its turn like any other, for the
clock's app duration or the board's **Display time**.

**Show on change** (on by default) switches the clock to the board whenever
its page changes, so the change is seen as it happens. Turned off, the page
changes quietly and shows on the board's next turn.

**Always on screen.** To show nothing but the board, switch off **Auto
transition** in the clock's settings, or leave the board alone in the
rotation.

**Animated page changes.** FiestaBoard's LED transitions (flip by default;
slide, wipe, cascade, dissolve, fade) are streamed as single frames at five a
second. Fade dims through black in six frames, or cross-fades with **Fade
style** Blend. A change only animates where it can be seen: with Show on
change off, a board that is not on screen just gets the new page.

**After a restart.** A pushed app lives in the clock's memory only and is gone
after a restart. The plugin reads the clock's uptime between page changes and,
when it restarted, has FiestaBoard send the page again.

**Left alone:** the clock's brightness, its other apps and its settings. The
plugin only pushes its own app and switches to it.

## Settings

| Setting | Default | |
|---|---|---|
| Clock address | — | IP address or local name, as `192.168.1.60` or `awtrixng-a1b2c3.local`. |
| App name | `FiestaBoard` | The app's name in the rotation and on the clock's **Apps** tab. Letters, digits, `-` and `_`, at most 32; empty is `FiestaBoard`. Give each board its own when several boards share one clock. |
| Show on change | on | Switch the clock to the board whenever its page changes. |
| Display time | the clock's | Seconds the board stays on screen in the rotation. |
| Tile style | Gaps | Seamless lights the line between two tiles of the same colour, so a row of tiles reads as one bar. |
| Block padding | Off | 1 pixel grows highlighted text's background by a pixel on every side. |
| Fade style | Through black | Or Blend. |
| User name, Password | — | Only when the clock's web UI asks for a password (`authEnabled`). The password is stored as a secret. |

### Find my clock

Asks every address of a /24 network for `GET /api/v1/device` (at most 64 at
a time, 10 s in all) and lists what answers like AWTRIX NG, with its name. It
searches, in order, the network you type (a /22 at most, private addresses
only), the network of the address you opened FiestaBoard at, and the network
FiestaBoard itself is on. Nothing outside your network is contacted.

A clock with a password answers no one and cannot be found this way: type its
address. `FIESTABOARD_OUTPUTS_ALLOW_HOSTS`, when set, limits which hosts are
contacted at all.

### Test connection

Reads the clock's state and says which AWTRIX NG version it runs. It tells
apart an unreachable or silent clock, a wrong password, a device that is not
AWTRIX NG, and an AWTRIX NG clock that is not a TC002.

## Removing a board

When you rename the app or remove the board, the old app stays on the clock
until it restarts. Delete it from the clock's **Apps** tab, or:

```sh
curl -X DELETE http://<clock>/api/v1/apps/FiestaBoard
```

## Verify on your clock

Taken from the AWTRIX NG documentation, still to be checked on a TC002:

| What | Assumed | Setting it affects |
|---|---|---|
| Stream rate | 5 frames a second all show | `maxFps` in `output/device-models.json` |
| Replacing the app while shown | Shows at once, without the clock's own app transition | every animated change |
| Switching with `fast` | Instant; the app's display time starts again | Show on change |

`tools/try_device.py` shows one page, waits five seconds, changes it with the
transition you name and prints every request with its timing. It runs once
and stops:

```sh
PYTHONPATH=/path/to/FiestaBoard python3 tools/try_device.py --host 192.168.1.60 --transition flip
```

Please open an issue with what you see, and your AWTRIX NG version.

## Development

Tests run against a FiestaBoard core checkout that has the output-plugin API
(the `next` branch):

```sh
./run_tests.sh /path/to/FiestaBoard
```

They use a mock clock on 127.0.0.1 (`tests/mock_awtrix.py`) that records every
request and can fail, hang, ask for a password or restart on purpose; a network
fence refuses any other host. The suite includes FiestaBoard's output-plugin
conformance suite and needs 80 % coverage. CI runs it on every push.

| File | Contents |
|---|---|
| `__init__.py` | The plugin: rendering, pushing, streaming, discovery, restart detection |
| `manifest.json` | Plugin id `awtrix_ng`, the board settings and actions |
| `output/device-models.json` | The `ulanzi_tc002` device model: 52 × 17 pixels, 3×5 font, 5 fps stream, with sources |
| `tools/try_device.py` | The one-off check against a real clock |

## Licence

MIT. AWTRIX NG is by [Blueforcer](https://github.com/Blueforcer/awtrix-ng).
