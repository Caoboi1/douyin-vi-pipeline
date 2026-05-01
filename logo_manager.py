#!/usr/bin/env python3
"""
Logo Manager - Upload, configure, and apply logos to videos
"""

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path
from PIL import Image, ImageTk
import json


class LogoManager:
    """Logo management interface"""

    def __init__(self, root):
        self.root = root
        self.root.title("🏷️ Logo Manager")
        self.root.geometry("1000x800")
        self.root.configure(bg="#1a1a1a")

        self.logo_dir = Path("./logos")
        self.logo_dir.mkdir(exist_ok=True)
        self.config_file = Path("logo_config.json")
        self.logos = {}
        self.selected_logo = None

        self.load_logos()
        self.setup_ui()

    def setup_ui(self):
        """Setup user interface"""
        # Top menu
        menu_frame = ttk.Frame(self.root)
        menu_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Button(menu_frame, text="📤 Import Logo", command=self.import_logo).pack(side=tk.LEFT, padx=5)
        ttk.Button(menu_frame, text="🗑️ Delete Logo", command=self.delete_logo).pack(side=tk.LEFT, padx=5)
        ttk.Button(menu_frame, text="💾 Save Config", command=self.save_config).pack(side=tk.LEFT, padx=5)

        # Main container
        main_container = ttk.Frame(self.root)
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Left: Logo list
        left_panel = ttk.Frame(main_container)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

        ttk.Label(left_panel, text="Available Logos", font=("Arial", 12, "bold")).pack()

        scrollbar = ttk.Scrollbar(left_panel)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.logo_listbox = tk.Listbox(
            left_panel,
            yscrollcommand=scrollbar.set,
            bg="#2a2a2a",
            fg="#00ff00",
            selectmode=tk.SINGLE,
            height=20
        )
        self.logo_listbox.pack(fill=tk.BOTH, expand=True)
        self.logo_listbox.bind("<<ListboxSelect>>", self.on_select_logo)
        scrollbar.config(command=self.logo_listbox.yview)

        # Right: Logo preview & settings
        right_panel = ttk.LabelFrame(main_container, text="Logo Settings", padding=10)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Preview
        ttk.Label(right_panel, text="Preview:", font=("Arial", 11, "bold")).pack(pady=(0, 10))
        self.preview_label = ttk.Label(right_panel, background="#333333")
        self.preview_label.pack(fill=tk.BOTH, expand=True, pady=(0, 20))

        # Settings frame
        settings_frame = ttk.LabelFrame(right_panel, text="Configuration", padding=10)
        settings_frame.pack(fill=tk.X, pady=10)

        # Name
        ttk.Label(settings_frame, text="Logo Name:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.name_entry = ttk.Entry(settings_frame, width=30)
        self.name_entry.grid(row=0, column=1, sticky=tk.W, padx=10)

        # Position
        ttk.Label(settings_frame, text="Default Position:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.position_var = tk.StringVar(value="bottom-right")
        ttk.Combobox(
            settings_frame,
            textvariable=self.position_var,
            values=["top-left", "top-right", "bottom-left", "bottom-right"],
            width=25,
            state="readonly"
        ).grid(row=1, column=1, sticky=tk.W, padx=10)

        # Opacity
        ttk.Label(settings_frame, text="Default Opacity:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.opacity_var = tk.DoubleVar(value=0.8)
        opacity_scale = ttk.Scale(
            settings_frame,
            from_=0.1, to=1.0,
            orient=tk.HORIZONTAL,
            variable=self.opacity_var
        )
        opacity_scale.grid(row=2, column=1, sticky=tk.EW, padx=10)

        # Size
        ttk.Label(settings_frame, text="Default Size (% of width):").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.size_var = tk.IntVar(value=10)
        ttk.Spinbox(
            settings_frame,
            from_=5, to=50,
            textvariable=self.size_var,
            width=10
        ).grid(row=3, column=1, sticky=tk.W, padx=10)

        # Info
        ttk.Separator(right_panel, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)

        info_frame = ttk.LabelFrame(right_panel, text="Information", padding=10)
        info_frame.pack(fill=tk.X)

        self.info_label = ttk.Label(
            info_frame,
            text="No logo selected",
            foreground="gray",
            justify=tk.LEFT
        )
        self.info_label.pack(fill=tk.X)

        # Buttons
        button_frame = ttk.Frame(right_panel)
        button_frame.pack(fill=tk.X, pady=10)

        ttk.Button(
            button_frame, text="✓ Save Settings", command=self.save_logo_settings, width=20
        ).pack(side=tk.LEFT, padx=5)

    def load_logos(self):
        """Load logos from directory"""
        self.logos = {}
        for logo_file in self.logo_dir.glob("*"):
            if logo_file.suffix.lower() in [".png", ".jpg", ".jpeg"]:
                name = logo_file.stem
                self.logos[name] = {
                    "path": str(logo_file),
                    "position": "bottom-right",
                    "opacity": 0.8,
                    "size_percent": 10
                }

        # Load config if exists
        if self.config_file.exists():
            try:
                with open(self.config_file, "r") as f:
                    config = json.load(f)
                    self.logos.update(config)
            except:
                pass

        self.refresh_listbox()

    def refresh_listbox(self):
        """Refresh logo listbox"""
        self.logo_listbox.delete(0, tk.END)

        for logo_name in sorted(self.logos.keys()):
            self.logo_listbox.insert(tk.END, f"🏷️  {logo_name}")

    def on_select_logo(self, event):
        """Handle logo selection"""
        selection = self.logo_listbox.curselection()
        if selection:
            logo_name = list(self.logos.keys())[selection[0]]
            self.selected_logo = logo_name
            logo_data = self.logos[logo_name]

            # Update UI
            self.name_entry.delete(0, tk.END)
            self.name_entry.insert(0, logo_name)
            self.position_var.set(logo_data.get("position", "bottom-right"))
            self.opacity_var.set(logo_data.get("opacity", 0.8))
            self.size_var.set(logo_data.get("size_percent", 10))

            # Show preview
            self.show_preview(logo_data["path"])

            # Show info
            logo_path = Path(logo_data["path"])
            size_mb = logo_path.stat().st_size / 1024 / 1024
            info_text = f"File: {logo_path.name}\nSize: {size_mb:.2f} MB\nPosition: {logo_data.get('position')}"
            self.info_label.config(text=info_text, foreground="white")

    def show_preview(self, image_path):
        """Show logo preview"""
        try:
            image = Image.open(image_path)
            image.thumbnail((200, 200), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(image)
            self.preview_label.config(image=photo)
            self.preview_label.image = photo  # Keep reference
        except Exception as e:
            self.info_label.config(text=f"Error loading preview: {str(e)}", foreground="red")

    def import_logo(self):
        """Import new logo"""
        try:
            path = filedialog.askopenfilename(
                filetypes=[("Image files", "*.png *.jpg *.jpeg"), ("All files", "*.*")]
            )
            if path:
                logo_path = Path(path)
                name = logo_path.stem

                # Check if name exists
                if name in self.logos:
                    result = messagebox.askyesno(
                        "Confirm",
                        f"Logo '{name}' already exists. Overwrite?"
                    )
                    if not result:
                        return

                # Copy to logos directory
                dest = self.logo_dir / logo_path.name
                dest.write_bytes(logo_path.read_bytes())

                self.logos[name] = {
                    "path": str(dest),
                    "position": "bottom-right",
                    "opacity": 0.8,
                    "size_percent": 10
                }

                self.refresh_listbox()
                messagebox.showinfo("Success", f"Logo '{name}' imported successfully!")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to import logo: {str(e)}")

    def delete_logo(self):
        """Delete selected logo"""
        if not self.selected_logo:
            messagebox.showwarning("Warning", "Please select a logo to delete")
            return

        result = messagebox.askyesno(
            "Confirm",
            f"Delete logo '{self.selected_logo}'?"
        )

        if result:
            try:
                logo_path = Path(self.logos[self.selected_logo]["path"])
                if logo_path.exists():
                    logo_path.unlink()

                del self.logos[self.selected_logo]
                self.refresh_listbox()
                self.preview_label.config(image="")
                self.info_label.config(text="No logo selected", foreground="gray")
                messagebox.showinfo("Success", "Logo deleted!")

            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete logo: {str(e)}")

    def save_logo_settings(self):
        """Save logo settings"""
        if not self.selected_logo:
            messagebox.showwarning("Warning", "Please select a logo")
            return

        try:
            new_name = self.name_entry.get()

            # Rename if needed
            if new_name != self.selected_logo:
                if new_name in self.logos and new_name != self.selected_logo:
                    messagebox.showwarning("Error", "Logo name already exists")
                    return

                self.logos[new_name] = self.logos.pop(self.selected_logo)
                self.selected_logo = new_name

            # Update settings
            self.logos[self.selected_logo]["position"] = self.position_var.get()
            self.logos[self.selected_logo]["opacity"] = self.opacity_var.get()
            self.logos[self.selected_logo]["size_percent"] = self.size_var.get()

            self.save_config()
            self.refresh_listbox()
            messagebox.showinfo("Success", "Logo settings saved!")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to save settings: {str(e)}")

    def save_config(self):
        """Save configuration to file"""
        try:
            with open(self.config_file, "w") as f:
                json.dump(self.logos, f, indent=2)
            print(f"✓ Configuration saved: {self.config_file}")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to save config: {str(e)}")


def main():
    root = tk.Tk()
    app = LogoManager(root)
    root.mainloop()


if __name__ == "__main__":
    main()
