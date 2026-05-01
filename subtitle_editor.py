#!/usr/bin/env python3
"""
Subtitle Editor - Edit, style, and manage SRT files
"""

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path
import pysrt
from dataclasses import dataclass


@dataclass
class SubtitleEntry:
    """Single subtitle entry"""
    index: int
    start: str
    end: str
    text: str

    def to_srt(self):
        """Convert to SRT format"""
        return f"{self.index}\n{self.start} --> {self.end}\n{self.text}\n"


class SubtitleEditor:
    """Subtitle file editor"""

    def __init__(self, root):
        self.root = root
        self.root.title("📝 Subtitle Editor")
        self.root.geometry("1200x700")
        self.root.configure(bg="#1a1a1a")

        self.srt_file = None
        self.subtitles = []
        self.current_index = 0

        self.setup_ui()

    def setup_ui(self):
        """Setup user interface"""
        # Top menu
        menu_frame = ttk.Frame(self.root)
        menu_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Button(menu_frame, text="📂 Open SRT", command=self.open_file).pack(side=tk.LEFT, padx=5)
        ttk.Button(menu_frame, text="💾 Save", command=self.save_file).pack(side=tk.LEFT, padx=5)
        ttk.Button(menu_frame, text="💾 Save As", command=self.save_as).pack(side=tk.LEFT, padx=5)
        ttk.Separator(menu_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=10)
        ttk.Button(menu_frame, text="➕ Add", command=self.add_subtitle).pack(side=tk.LEFT, padx=5)
        ttk.Button(menu_frame, text="➖ Delete", command=self.delete_subtitle).pack(side=tk.LEFT, padx=5)

        self.file_label = ttk.Label(menu_frame, text="No file loaded", foreground="gray")
        self.file_label.pack(side=tk.RIGHT, padx=10)

        # Main container
        main_container = ttk.Frame(self.root)
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Left: Subtitle list
        left_panel = ttk.Frame(main_container)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

        ttk.Label(left_panel, text="Subtitles", font=("Arial", 11, "bold")).pack()

        # Listbox with scrollbar
        scrollbar = ttk.Scrollbar(left_panel)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.subtitle_listbox = tk.Listbox(
            left_panel,
            yscrollcommand=scrollbar.set,
            bg="#2a2a2a",
            fg="#00ff00",
            selectmode=tk.SINGLE
        )
        self.subtitle_listbox.pack(fill=tk.BOTH, expand=True)
        self.subtitle_listbox.bind("<<ListboxSelect>>", self.on_select_subtitle)
        scrollbar.config(command=self.subtitle_listbox.yview)

        # Right: Subtitle editor
        right_panel = ttk.LabelFrame(main_container, text="Edit Subtitle", padding=10)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Index (read-only)
        ttk.Label(right_panel, text="Index:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.index_label = ttk.Label(right_panel, text="--", font=("Arial", 12, "bold"))
        self.index_label.grid(row=0, column=1, sticky=tk.W, padx=10)

        # Start time
        ttk.Label(right_panel, text="Start Time:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.start_entry = ttk.Entry(right_panel, width=30)
        self.start_entry.grid(row=1, column=1, sticky=tk.W, padx=10)

        # End time
        ttk.Label(right_panel, text="End Time:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.end_entry = ttk.Entry(right_panel, width=30)
        self.end_entry.grid(row=2, column=1, sticky=tk.W, padx=10)

        # Text
        ttk.Label(right_panel, text="Text:").grid(row=3, column=0, sticky=tk.NW, pady=5)
        self.text_editor = tk.Text(right_panel, height=8, width=35)
        self.text_editor.grid(row=3, column=1, sticky=tk.NSEW, padx=10, pady=5)

        # Update button
        ttk.Button(
            right_panel, text="✓ Update Subtitle", command=self.update_subtitle, width=25
        ).grid(row=4, column=0, columnspan=2, pady=10)

        # Search/Filter
        ttk.Label(right_panel, text="Search:").grid(row=5, column=0, sticky=tk.W, pady=5)
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(right_panel, textvariable=self.search_var, width=30)
        search_entry.grid(row=5, column=1, sticky=tk.W, padx=10)
        search_entry.bind("<KeyRelease>", lambda e: self.filter_subtitles())

        # Statistics
        ttk.Separator(right_panel, orient=tk.HORIZONTAL).grid(row=6, column=0, columnspan=2, sticky=tk.EW, pady=10)
        self.stats_label = ttk.Label(right_panel, text="Total: 0 subtitles", font=("Arial", 10))
        self.stats_label.grid(row=7, column=0, columnspan=2, sticky=tk.W, pady=5)

    def open_file(self):
        """Open SRT file"""
        try:
            path = filedialog.askopenfilename(
                filetypes=[("SRT files", "*.srt"), ("All files", "*.*")]
            )
            if path:
                self.srt_file = path
                srt_data = pysrt.load(path)

                self.subtitles = [
                    SubtitleEntry(
                        index=sub.index,
                        start=str(sub.start),
                        end=str(sub.end),
                        text=sub.text
                    )
                    for sub in srt_data
                ]

                self.file_label.config(text=f"📄 {Path(path).name}", foreground="green")
                self.refresh_listbox()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to open file: {str(e)}")

    def save_file(self):
        """Save SRT file"""
        if not self.srt_file:
            self.save_as()
            return

        try:
            srt_output = pysrt.SubRipFile()
            for sub_entry in self.subtitles:
                sub = pysrt.SubRip()
                sub.index = sub_entry.index
                sub.start = pysrt.SubRipTime.colon_separated_to_ms(sub_entry.start)
                sub.end = pysrt.SubRipTime.colon_separated_to_ms(sub_entry.end)
                sub.text = sub_entry.text
                srt_output.append(sub)

            srt_output.save(self.srt_file, encoding="utf-8")
            messagebox.showinfo("Success", "File saved successfully!")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to save file: {str(e)}")

    def save_as(self):
        """Save as new file"""
        try:
            path = filedialog.asksaveasfilename(
                defaultextension=".srt",
                filetypes=[("SRT files", "*.srt")]
            )
            if path:
                self.srt_file = path
                self.save_file()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to save: {str(e)}")

    def add_subtitle(self):
        """Add new subtitle"""
        try:
            if not self.subtitles:
                new_index = 1
                new_start = "00:00:00,000"
                new_end = "00:00:05,000"
            else:
                new_index = max(s.index for s in self.subtitles) + 1
                last_sub = self.subtitles[-1]
                new_start = last_sub.end
                new_end = str(pysrt.SubRipTime.from_string(last_sub.end) + 5000)

            new_sub = SubtitleEntry(
                index=new_index,
                start=new_start,
                end=new_end,
                text="New subtitle"
            )
            self.subtitles.append(new_sub)
            self.refresh_listbox()
            self.current_index = len(self.subtitles) - 1
            self.subtitle_listbox.selection_clear(0, tk.END)
            self.subtitle_listbox.selection_set(self.current_index)
            self.on_select_subtitle(None)

        except Exception as e:
            messagebox.showerror("Error", f"Failed to add subtitle: {str(e)}")

    def delete_subtitle(self):
        """Delete selected subtitle"""
        if self.current_index < 0 or self.current_index >= len(self.subtitles):
            messagebox.showwarning("Warning", "Please select a subtitle to delete")
            return

        self.subtitles.pop(self.current_index)

        # Re-index
        for i, sub in enumerate(self.subtitles, 1):
            sub.index = i

        self.refresh_listbox()

    def on_select_subtitle(self, event):
        """Handle subtitle selection"""
        selection = self.subtitle_listbox.curselection()
        if selection:
            self.current_index = selection[0]
            sub = self.subtitles[self.current_index]

            self.index_label.config(text=str(sub.index))
            self.start_entry.delete(0, tk.END)
            self.start_entry.insert(0, sub.start)
            self.end_entry.delete(0, tk.END)
            self.end_entry.insert(0, sub.end)
            self.text_editor.delete("1.0", tk.END)
            self.text_editor.insert("1.0", sub.text)

    def update_subtitle(self):
        """Update selected subtitle"""
        if self.current_index < 0 or self.current_index >= len(self.subtitles):
            messagebox.showwarning("Warning", "Please select a subtitle to update")
            return

        try:
            sub = self.subtitles[self.current_index]
            sub.start = self.start_entry.get()
            sub.end = self.end_entry.get()
            sub.text = self.text_editor.get("1.0", tk.END).strip()

            self.refresh_listbox()
            messagebox.showinfo("Success", "Subtitle updated!")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to update: {str(e)}")

    def filter_subtitles(self):
        """Filter subtitles by search text"""
        search_text = self.search_var.get().lower()

        self.subtitle_listbox.delete(0, tk.END)

        for i, sub in enumerate(self.subtitles):
            if search_text in sub.text.lower() or search_text in str(sub.index):
                self.subtitle_listbox.insert(
                    tk.END,
                    f"[{sub.index}] {sub.text[:50]}" + ("..." if len(sub.text) > 50 else "")
                )

    def refresh_listbox(self):
        """Refresh subtitle listbox"""
        self.subtitle_listbox.delete(0, tk.END)

        for sub in self.subtitles:
            display_text = f"[{sub.index}] {sub.start} --> {sub.end}"
            if sub.text:
                display_text += f"\n    {sub.text[:40]}" + ("..." if len(sub.text) > 40 else "")

            self.subtitle_listbox.insert(tk.END, display_text)

        # Update stats
        self.stats_label.config(text=f"Total: {len(self.subtitles)} subtitles")


def main():
    root = tk.Tk()
    app = SubtitleEditor(root)
    root.mainloop()


if __name__ == "__main__":
    main()
