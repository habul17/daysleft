"""The Days Left settings window (GTK 4 + libadwaita).

Pick a style, what to count, colours and an optional photo, with a live
preview. Every change is saved and applied to the desktop straight away.
"""

import sys
from datetime import date
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gio, GLib, Gtk  # noqa: E402
from PIL import Image  # noqa: E402

from . import backends, settings as config  # noqa: E402
from .render import render  # noqa: E402
from .year import year_status  # noqa: E402

APP_ID = "local.daysleft.DaysLeft"
PACKAGE_PARENT = str(Path(__file__).resolve().parent.parent)
PREVIEW_WIDTH = 960  # pixels rendered for the preview
PREVIEW_HEIGHT = 250  # height it is shown at in the window
APPLY_DELAY_MS = 400  # wait for a pause in changes before setting the wallpaper
IMAGE_TYPES = ["image/jpeg", "image/png", "image/webp", "image/bmp", "image/tiff"]

CSS = """
.preview { border-radius: 12px; }
.swatch {
  min-width: 26px; min-height: 26px; padding: 0; border-radius: 999px;
  box-shadow: inset 0 0 0 1px alpha(currentColor, 0.15);
}
.swatch:checked { outline: 2px solid var(--accent-bg-color); outline-offset: 2px; }
.swatch-neutral { background: linear-gradient(135deg, #f6f5f4 50%, #241f31 50%); }
""" + "".join(
    f".swatch-{name} {{ background: rgb{color}; }}\n"
    for name, color in config.ACCENTS.items() if color
)


class Window(Adw.ApplicationWindow):
    def __init__(self, app: Adw.Application):
        super().__init__(application=app, title="Days Left", default_width=620, default_height=760)
        self.app = app
        self.settings = config.load()
        self._apply_source = 0
        self._applying = False
        self._apply_again = False

        width, height = backends.detect().screen_size()
        self.preview_size = (PREVIEW_WIDTH, round(PREVIEW_WIDTH * height / width))
        self.preview = Gtk.Picture(can_shrink=True, content_fit=Gtk.ContentFit.FILL,
                                   overflow=Gtk.Overflow.HIDDEN)
        self.preview.add_css_class("preview")
        self.preview.add_css_class("card")

        page = Adw.PreferencesPage()
        preview_group = Adw.PreferencesGroup()
        frame = Gtk.AspectFrame(ratio=width / height, obey_child=False, child=self.preview)
        frame.set_size_request(-1, PREVIEW_HEIGHT)
        preview_group.add(frame)
        page.add(preview_group)

        wallpaper = Adw.PreferencesGroup(title="Wallpaper")
        wallpaper.add(self._choice_row("Style", "style", config.STYLES))
        wallpaper.add(self._choice_row("Shows", "unit", config.UNITS))
        wallpaper.add(self._photo_row())
        page.add(wallpaper)

        colors = Adw.PreferencesGroup(title="Colors")
        colors.add(self._choice_row("Theme", "theme", config.THEMES))
        colors.add(self._accent_row())
        page.add(colors)

        self.toasts = Adw.ToastOverlay(child=page)
        view = Adw.ToolbarView(content=self.toasts)
        view.add_top_bar(Adw.HeaderBar())
        self.set_content(view)

        Adw.StyleManager.get_default().connect("notify::dark", lambda *_: self._refresh_preview())
        self.connect("close-request", self._on_close)
        self._refresh_preview()

    def _choice_row(self, title, key, choices):
        values = list(choices)
        row = Adw.ComboRow(title=title, model=Gtk.StringList.new(list(choices.values())))
        row.set_selected(values.index(getattr(self.settings, key)))
        row.connect("notify::selected", lambda row, _: self._change(key, values[row.get_selected()]))
        return row

    def _accent_row(self):
        row = Adw.ActionRow(title="Accent")
        swatches = Gtk.Box(spacing=10, valign=Gtk.Align.CENTER)
        group = None
        for name in config.ACCENTS:
            button = Gtk.ToggleButton(tooltip_text=name.capitalize(), valign=Gtk.Align.CENTER,
                                      active=name == self.settings.accent)
            button.add_css_class("swatch")
            button.add_css_class(f"swatch-{name}")
            button.set_group(group)
            group = group or button
            button.connect("toggled", self._on_accent_toggled, name)
            swatches.append(button)
        row.add_suffix(swatches)
        return row

    def _on_accent_toggled(self, button, name):
        if button.get_active():
            self._change("accent", name)

    def _photo_row(self):
        self.photo_row = Adw.ActionRow(title="Photo")
        choose = Gtk.Button(label="Choose…", valign=Gtk.Align.CENTER)
        choose.connect("clicked", self._choose_photo)
        self.remove_photo_button = Gtk.Button(icon_name="user-trash-symbolic", valign=Gtk.Align.CENTER,
                                              tooltip_text="Remove photo")
        self.remove_photo_button.add_css_class("flat")
        self.remove_photo_button.connect("clicked", self._remove_photo)
        self.photo_row.add_suffix(choose)
        self.photo_row.add_suffix(self.remove_photo_button)
        self._update_photo_row()
        return self.photo_row

    def _update_photo_row(self):
        has_photo = self.settings.photo is not None
        self.photo_row.set_subtitle("Your photo, dimmed so the counter stays readable"
                                    if has_photo else "None — plain background")
        self.remove_photo_button.set_visible(has_photo)

    def _choose_photo(self, _button):
        images = Gtk.FileFilter(name="Images")
        for mime_type in IMAGE_TYPES:
            images.add_mime_type(mime_type)
        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(images)
        dialog = Gtk.FileDialog(title="Choose a Photo", filters=filters, default_filter=images)
        dialog.open(self, None, self._on_photo_chosen)

    def _on_photo_chosen(self, dialog, result):
        try:
            path = dialog.open_finish(result).get_path()
        except GLib.Error:
            return  # dialog cancelled
        try:
            with Image.open(path) as image:
                image.verify()
            photo = config.import_photo(Path(path))
        except Exception:  # Pillow raises assorted error types for bad images
            self.toasts.add_toast(Adw.Toast(title="Couldn't open that image"))
            return
        self._change("photo", photo)
        self._update_photo_row()

    def _remove_photo(self, _button):
        config.remove_photo()
        self._change("photo", None)
        self._update_photo_row()

    def _change(self, key, value):
        setattr(self.settings, key, value)
        config.save(self.settings)
        self._refresh_preview()
        if self._apply_source:
            GLib.source_remove(self._apply_source)
        self._apply_source = GLib.timeout_add(APPLY_DELAY_MS, self._apply)

    def _refresh_preview(self):
        theme = self.settings.theme
        dark = Adw.StyleManager.get_default().get_dark() if theme == "system" else theme == "dark"
        image = render(year_status(date.today()), *self.preview_size, self.settings, dark)
        width, height = image.size
        self.preview.set_paintable(Gdk.MemoryTexture.new(
            width, height, Gdk.MemoryFormat.R8G8B8, GLib.Bytes.new(image.tobytes()), width * 3))

    def _apply(self):
        """Sets the wallpaper in a separate process, so the window never stalls.
        Runs one at a time, so an older run can't finish last and win."""
        self._apply_source = 0
        if self._applying:
            self._apply_again = True
            return GLib.SOURCE_REMOVE
        self._applying = True
        self.app.hold()  # keep running until it's done, even if the window closes
        launcher = Gio.SubprocessLauncher.new(Gio.SubprocessFlags.NONE)
        launcher.setenv("PYTHONPATH", PACKAGE_PARENT, True)
        process = launcher.spawnv([sys.executable, "-m", "daysleft", "apply"])
        process.wait_check_async(None, self._on_applied)
        return GLib.SOURCE_REMOVE

    def _on_applied(self, process, result):
        self._applying = False
        try:
            process.wait_check_finish(result)
        except GLib.Error:
            self.toasts.add_toast(Adw.Toast(title="Couldn't set the wallpaper"))
        if self._apply_again:
            self._apply_again = False
            self._apply()
        self.app.release()

    def _on_close(self, _window):
        if self._apply_source:  # a change is still waiting for its delay
            GLib.source_remove(self._apply_source)
            self._apply()
        return False


def run() -> None:
    app = Adw.Application(application_id=APP_ID)

    def on_startup(app):
        css = Gtk.CssProvider()
        css.load_from_string(CSS)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        Gtk.Window.set_default_icon_name(APP_ID)

    def on_activate(app):
        (app.get_active_window() or Window(app)).present()

    app.connect("startup", on_startup)
    app.connect("activate", on_activate)
    app.run([sys.argv[0]])
