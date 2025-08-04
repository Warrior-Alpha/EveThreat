import tkinter as tk
from tkinter import ttk
import threading
import time
import pyperclip
import requests
import queue
import re
from PIL import Image, ImageTk
from io import BytesIO
import webbrowser
import os
from tkinter import messagebox


OPT_IN_CLIPBOARD = False
RECENT_VALUE = ""

def check_name_validity(char_name):
    if len(char_name) < 3 or len(char_name) > 37 or char_name.count(' ') > 2:
        return False
    regex = r"[^ 'a-zA-Z0-9-]"
    if re.search(regex, char_name):
        return False
    return True


def analyze_chars(char_names, result_queue):
    try:
        response = requests.post("", json={"names": char_names})
        response.raise_for_status()
        result_queue.put(response.json())
    except Exception as e:
        pass


def clipboard_watcher(result_queue, stop_event):
    global RECENT_VALUE
    while not stop_event.is_set():
        try:
            clipboard = pyperclip.paste()
            if clipboard != RECENT_VALUE and OPT_IN_CLIPBOARD:
                RECENT_VALUE = clipboard
                char_names = clipboard.strip().splitlines()
                if len(char_names) > 3500:
                    time.sleep(0.5)
                    continue
                if not all(check_name_validity(name) for name in char_names):
                    time.sleep(0.5)
                    continue
                threading.Thread(target=analyze_chars, args=(char_names, result_queue)).start()
        except:
            pass
        time.sleep(0.5)


class EveThreatApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Eve Threat")
        self.geometry("1100x500")
        icon_path = os.path.join(os.path.dirname(__file__), "icon.ico")
        self.iconbitmap(icon_path)
        self.configure(bg="#1e1e1e")
        self.resizable(True, True)
        header_frame = tk.Frame(self, bg="#1e1e1e")
        header_frame.pack(fill="x", pady=(10, 0), padx=10)

        heading = tk.Label(header_frame, text="Eve Threat",
                           font=("Segoe UI", 18, "bold"),
                           fg="white", bg="#1e1e1e")
        heading.pack(side="left")
        # === Define columns ===
        self.columns = [
            "Name",
            "Kills",
            "Losses",
            "Covert Cyno",
            "Hard Cyno",
            "Indy Cyno",
            "Last lost ship",
            "Last killed with ship",
            "Blops kills",
            "Last blops kill"
        ]
        button_frame = tk.Frame(header_frame, bg="#1e1e1e")
        button_frame.pack(side="right")

        self.ignore_count = 0
        self.ignore_set = set()

        self.ignore_label = tk.Label(button_frame, text=f"Ignored ({self.ignore_count})",
                                     fg="white", bg="#1e1e1e", font=("Segoe UI", 10), cursor="hand2")
        self.ignore_label.pack(side="left", padx=(0, 20))
        self.ignore_label.bind("<Button-1>", self.reset_ignored)

        changelog_btn = tk.Button(button_frame, text="Changelog", command=self.show_changelog,
                                  bg="#2e2e2e", fg="white", relief="flat", cursor="hand2", padx=10)
        changelog_btn.pack(side="left", padx=(0, 10))

        about_btn = tk.Button(button_frame, text="About", command=self.show_about,
                              bg="#2e2e2e", fg="white", relief="flat", cursor="hand2", padx=10)
        about_btn.pack(side="left")

        self.add_hover_effect(about_btn)
        self.add_hover_effect(changelog_btn)
        # === Container frame for treeview + scrollbar ===
        container = tk.Frame(self)
        container.pack(expand=True, fill="both", padx=10, pady=10)
        # === Treeview ===
        self.tree = ttk.Treeview(container, columns=self.columns, show="headings", style="Dark.Treeview")
        self._hovered_row = None
        self.tree.bind("<Motion>", self.on_row_hover)
        self.tree.bind("<Motion>", self.on_mouse_motion)
        self.tree.bind("<Leave>", self.on_mouse_leave)
        self.tree.bind("<Button-1>", self.on_row_click)
        self.tooltip = ToolTip(self.tree)
        self.tree.bind("<Motion>", self.on_tree_hover)
        self.tree.bind("<Leave>", lambda e: self.tooltip.hidetip())
        self.tree.bind("<Button-3>", self.show_context_menu)
        self.context_menu = tk.Menu(self, tearoff=0, bg="#2e2e2e", fg="white", activebackground="#444444",
                                    activeforeground="white")
        self.context_menu.add_command(label="Ignore Character", command=self.ignore_selected_character)
        self._last_row = None
        self._sort_column_state = {}
        self._current_sorted_col = None
        self._current_sort_reverse = False
        for col in self.columns:
            self.tree.heading(col, text=col, command=lambda _col=col: self.sort_by_column(_col))
            self.tree.column(col, anchor="center", width=100, stretch=True)

        self.tree.pack(side="left", fill="both", expand=True)

        self.clipboard_monitoring = tk.BooleanVar(value=False)
        self.checkbox = tk.Checkbutton(text="Allow access to my clipboard",
                                        variable=self.clipboard_monitoring, command=self.toggle_clipboard_access)
        self.checkbox.pack(pady=5)

        # Analyze Clipboard button
        self.analyze_button = tk.Button(text="Analyze clipboard", command=self.manual_analyze_clipboard)
        if self.clipboard_monitoring.get():
            self.analyze_button.pack_forget()
        else:
            self.analyze_button.pack(pady=5)


        # === Scrollbar ===
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=self.tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scrollbar.set)

        # === Dark Style ===
        style = ttk.Style(self)
        style.theme_use("default")
        style.configure("Dark.Treeview",
                        background="#2e2e2e",
                        foreground="#ffffff",
                        rowheight=25,
                        fieldbackground="#2e2e2e",
                        bordercolor="#3c3c3c",
                        borderwidth=1)
        style.configure("Dark.Treeview.Heading",
                        background="#3c3c3c",
                        foreground="#ffffff",
                        relief="flat")
        style.map("Dark.Treeview.Heading",
                  background=[("active", "#444")])
        self.tree.tag_configure("yellow", background="#5c5c00", foreground="white")
        self.tree.tag_configure("red", background="#661111", foreground="white")
        self.tree.tag_configure("evenrow", background="#2e2e2e")
        self.tree.tag_configure("oddrow", background="#262626")
        self.tree.tag_configure('hover', background="#333333")

        self.result_queue = queue.Queue()
        self.stop_event = threading.Event()

        threading.Thread(target=clipboard_watcher, args=(self.result_queue, self.stop_event), daemon=True).start()
        self.after(100, self.process_queue)

    def show_context_menu(self, event):
        row_id = self.tree.identify_row(event.y)
        if row_id:
            self.tree.selection_set(row_id)
            self.context_menu.post(event.x_root, event.y_root)

    def ignore_selected_character(self):
        selected = self.tree.selection()
        if selected:
            char_id = selected[0]
            self.ignore_set.add(char_id)
            self.tree.delete(char_id)
            self.update_ignored_counter()

    def reset_ignored(self):
        self.ignore_set.clear()
        self.ignore_count = 0
        self.ignore_label.config(text=f"Ignored ({self.ignore_count})")

    def update_ignored_counter(self):
        count = len(self.ignore_set)
        self.ignore_label.config(text=f"Ignored ({count})")

    def on_tree_hover(self, event):
        region = self.tree.identify("region", event.x, event.y)
        column = self.tree.identify_column(event.x)
        row_id = self.tree.identify_row(event.y)

        # Only change cursor if we're hovering over the "Name" column
        if region == "cell" and column == "#1" and row_id:
            self.tree.config(cursor="hand2")
        else:
            self.tree.config(cursor="")
        row_id = self.tree.identify_row(event.y)
        col = self.tree.identify_column(event.x)

        if row_id and col == '#1':  # Hovering over Name column
            x, y, _, _ = self.tree.bbox(row_id, col)
            abs_x = self.tree.winfo_rootx() + x
            abs_y = self.tree.winfo_rooty() + y
            self.tooltip.showtip("Open zKillboard", abs_x, abs_y)
        else:
            self.tooltip.hidetip()

    def on_mouse_motion(self, event):
        region = self.tree.identify("region", event.x, event.y)
        column = self.tree.identify_column(event.x)
        row_id = self.tree.identify_row(event.y)

        # Only change cursor if we're hovering over the "Name" column
        if region == "cell" and column == "#1" and row_id:
            self.tree.config(cursor="hand2")
        else:
            self.tree.config(cursor="")

    def on_mouse_leave(self):
        self.tree.config(cursor="")

    def on_row_click(self, event):
        column = self.tree.identify_column(event.x)
        row_id = self.tree.identify_row(event.y)

        if column == "#1" and row_id and row_id.isdigit():  # "#1" is the first column ("Name")
            url = f"https://zkillboard.com/character/{row_id}/"
            webbrowser.open_new_tab(url)

    def on_row_hover(self, event):
        row_id = self.tree.identify_row(event.y)

        if self._hovered_row and self._hovered_row != row_id:
            index = self.tree.index(self._hovered_row)
            base_tag = 'evenrow' if index % 2 == 0 else 'oddrow'
            self.tree.item(self._hovered_row, tags=(base_tag,))

        if row_id:
            self.tree.item(row_id, tags=('hover',))
            self._hovered_row = row_id

    def sort_by_column(self, col, force_reverse=None):
        data = [(self.tree.set(child, col), child) for child in self.tree.get_children('')]

        try:
            data.sort(key=lambda t: float(t[0].replace(',', '')))
        except ValueError:
            data.sort(key=lambda t: t[0].lower())

        reverse = force_reverse if force_reverse is not None else self._sort_column_state.get(col, False)
        data = data[::-1] if reverse else data
        self._sort_column_state[col] = not reverse

        # Store current sort state
        self._current_sorted_col = col
        self._current_sort_reverse = reverse

        for index, (val, item) in enumerate(data):
            self.tree.move(item, '', index)

        for c in self.columns:
            heading = c
            if c == col:
                arrow = "▲" if not reverse else "▼"
                heading += f" {arrow}"
            self.tree.heading(c, text=heading, command=lambda _col=c: self.sort_by_column(_col))

    def add_hover_effect(self, button, hover_bg="#444", normal_bg="#2e2e2e"):
        def on_enter(e):
            button.configure(bg=hover_bg)

        def on_leave(e):
            button.configure(bg=normal_bg)

        button.bind("<Enter>", on_enter)
        button.bind("<Leave>", on_leave)

    def show_changelog(self):
        changelog_window = tk.Toplevel(self)
        changelog_window.title("Changelog")
        changelog_window.configure(bg="#1e1e1e")
        changelog_window.geometry("500x300")

        try:
            icon_path = os.path.join(os.path.dirname(__file__), "icon.ico")
            changelog_window.iconbitmap(icon_path)
        except:
            pass

        changelog = (
            "v1.0\n"
            "- Initial release.\n"
            "- Clipboard monitoring.\n"
            "- Fetch characters via an API.\n"
            "- Ignore by right clicking and reset by clicking on the \"ignore\" counter.\n\n"
            "v1.1\n"
            "- Added opt-in for clipboard access"
        )

        label = tk.Label(changelog_window,
                         text=changelog,
                         font=("Segoe UI", 10),
                         fg="white",
                         bg="#1e1e1e",
                         justify="left",
                         anchor="nw")
        label.pack(padx=20, pady=20, fill="both", expand=True)
        close_btn = tk.Button(
            changelog_window,
            text="Close",
            command=changelog_window.destroy,
            bg="#2e2e2e",
            fg="white",
            relief="flat",
            cursor="hand2"
        )
        close_btn.pack(pady=(10, 20))
        self.add_hover_effect(close_btn)

    def show_about(self):
        about_window = tk.Toplevel(self)
        about_window.title("About")
        about_window.configure(bg="#1e1e1e")
        about_window.geometry("400x600")

        try:
            icon_path = os.path.join(os.path.dirname(__file__), "icon.ico")
            about_window.iconbitmap(icon_path)
        except:
            pass  # Skip icon if not found or unsupported on platform

        # Load and display image from EVE Online API
        try:
            url = "https://images.evetech.net/characters/1013841685/portrait?size=128"
            response = requests.get(url)
            response.raise_for_status()
            image_data = BytesIO(response.content)
            image = Image.open(image_data).resize((128, 128))
            photo = ImageTk.PhotoImage(image)

            image_label = tk.Label(about_window, image=photo, bg="#1e1e1e")
            image_label.image = photo
            image_label.pack(pady=10)
        except Exception as e:
            fallback = tk.Label(about_window, text="(Image failed to load)", fg="gray", bg="#1e1e1e")
            fallback.pack(pady=10)

        frame = tk.Frame(about_window, bg="#1e1e1e")
        frame.pack()

        tk.Label(frame, text="Eve Threat by ", font=("Segoe UI", 11), fg="white", bg="#1e1e1e").pack(side="left")
        tk.Label(frame, text="Warrior Alpha", font=("Segoe UI", 11, "bold"), fg="white", bg="#1e1e1e").pack(side="left")

        # Then add the rest of the text in another label below
        rest_text = (
            "\n\nMade for EVE Online players!\n"
            "This tool helps you quickly check characters by simply copying their names from a chat channel (like Local).\n"
            "All data is fetched automatically from our self-hosted server — no files are stored locally.\n\n"
            "If you find Eve Threat helpful and would like to support its development,\n"
            "feel free to send ISK in-game to:\nWarrior Alpha\n\n"
            "Your support is greatly appreciated!"
        )

        tk.Label(about_window, text=rest_text, font=("Segoe UI", 11), fg="white", bg="#1e1e1e", justify="center",
                 wraplength=350).pack()
        close_btn = tk.Button(
            about_window,
            text="Close",
            command=about_window.destroy,
            bg="#2e2e2e",
            fg="white",
            relief="flat",
            cursor="hand2"
        )
        close_btn.pack(pady=(10, 20))
        self.add_hover_effect(close_btn)

    def process_queue(self):
        while not self.result_queue.empty():
            data = self.result_queue.get()
            self.tree.delete(*self.tree.get_children())
            if isinstance(data, list):
                rows = []
                for index, item in enumerate(data):
                    name_with_icon = item.get("Name", "") + " 🔗"
                    row = [name_with_icon] + [item.get(col, "") for col in self.columns[1:]]
                    char_id = item.get("id")

                    try:
                        losses = int(item.get("Losses", 0))
                        covert = int(item.get("Covert Cyno", 0))
                        hard = int(item.get("Hard Cyno", 0))
                    except (ValueError, TypeError):
                        losses = covert = hard = 0

                    tags = []
                    if losses > 0:
                        covert_pct = (covert / losses) * 100
                        hard_pct = (hard / losses) * 100

                        if hard_pct or covert_pct:
                            if 10 < covert_pct <= 50 or 10 < hard_pct <= 50:
                                tags.append("yellow")
                            elif covert_pct > 50 or hard_pct > 50:
                                tags.append("red")

                    if not tags:
                        tags.append("evenrow" if index % 2 == 0 else "oddrow")
                    if self._current_sorted_col:
                        self.sort_by_column(self._current_sorted_col, force_reverse=self._current_sort_reverse)
                    if char_id and str(char_id) not in self.ignore_set:
                        self.tree.insert("", "end", iid=str(char_id), values=row, tags=tags)
        self.after(100, self.process_queue)

    def on_close(self):
        self.stop_event.set()
        self.destroy()

    def toggle_clipboard_access(self):
        global OPT_IN_CLIPBOARD
        if self.clipboard_monitoring.get():
            OPT_IN_CLIPBOARD = True
            self.analyze_button.pack_forget()
        else:
            OPT_IN_CLIPBOARD = False
            self.analyze_button.pack(pady=5)

    def manual_analyze_clipboard(self):
        global RECENT_VALUE
        try:
            if pyperclip.paste() != RECENT_VALUE:
                RECENT_VALUE = pyperclip.paste()
                char_names = RECENT_VALUE.strip().splitlines()
                if len(char_names) > 3500:
                    return False
                if not all(check_name_validity(name) for name in char_names):
                    return False
                threading.Thread(target=analyze_chars, args=(char_names, self.result_queue)).start()
            return False
        except tk.TclError:
            messagebox.showerror("Error", "Unable to read clipboard.")


class ToolTip:
    def __init__(self, widget):
        self.widget = widget
        self.tipwindow = None

    def showtip(self, text, x, y):
        if self.tipwindow:
            return
        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.configure(bg="#2e2e2e", padx=6, pady=2)
        label = tk.Label(tw, text=text, justify='left',
                         background="#2e2e2e", foreground="white",
                         relief="solid", borderwidth=1,
                         font=("Segoe UI", 9))
        label.pack()
        tw.wm_geometry(f"+{x+20}+{y+10}")

    def hidetip(self):
        if self.tipwindow:
            self.tipwindow.destroy()
            self.tipwindow = None


if __name__ == "__main__":
    EveThreatApp().mainloop()
