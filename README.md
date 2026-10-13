# Days Left

A minimal wallpaper that shows how many days are left in the year. It redraws
itself every midnight, and a small settings app lets you choose how it looks.

v1 supports GNOME (tested on Ubuntu 26.04, GNOME 50, Wayland). Other Linux
desktops, Windows and macOS are planned for v2.

## Install

```sh
./install.sh
```

Then open **Days Left** from the app grid to choose the look. Needs
`python3-pil`, `python3-gi` and `gir1.2-adw-1`, which Ubuntu ships by default.

## Options

| Option  | Choices                                             |
|---------|-----------------------------------------------------|
| Style   | Corner, Centered, Year in dots, Progress ring       |
| Shows   | Days left, Weeks left, % of year gone, Challenge day |
| Photo   | Plain background, or any photo (dimmed for contrast) |
| Theme   | Match system, Dark, Light                           |
| Accent  | Neutral or one of GNOME's eight accent colours      |

Changes apply to the desktop straight away. With **Match system**, GNOME gets a
light and a dark wallpaper and switches with your system style. A chosen photo
is copied into `~/.local/share/daysleft/`, so moving the original is fine.

**Challenge day** counts up from a start date you pick, which is day 1, for a
bootcamp, a 100-day challenge or a habit streak. With the name set to `100X`,
the day after the start reads "2 · DAYS IN 100X". Before the start date it
counts down instead.

## Uninstall

```sh
./uninstall.sh
```

This also brings back the wallpaper you had before installing.

## How it works

- `daysleft/render.py` draws the wallpaper with Pillow; `daysleft/app.py` is the
  GTK 4 / libadwaita settings window; `daysleft/backends/gnome.py` sets the
  wallpaper through GSettings. Each new desktop gets its own backend module.
- Settings are saved to `~/.config/daysleft/settings.json`.
- `systemd/` holds a user timer that runs just after midnight, and catches up
  after sleep or shutdown. The service also runs at every login.

## Handy commands

```sh
# Open the settings window
python3 -m daysleft settings

# Preview a date with your saved settings, without changing the wallpaper
python3 -m daysleft preview /tmp/preview.png --date 2026-12-31

# Re-apply now / check the timer / see logs
systemctl --user start daysleft.service
systemctl --user list-timers daysleft.timer
journalctl --user -u daysleft.service

# Run the tests
python3 -m unittest
```

After changing code, run `./install.sh` again to update the installed copy.
