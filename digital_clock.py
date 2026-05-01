#!/usr/bin/env python3
"""
Digital Clock - Display current time in different time zones
Shows time in multiple zones with real-time updates
"""

import tkinter as tk
from tkinter import font
from datetime import datetime
import pytz
from typing import List, Tuple


class DigitalClock:
    """Digital clock displaying multiple time zones"""

    def __init__(self, root: tk.Tk, timezones: List[Tuple[str, str]] = None):
        """
        Initialize digital clock

        Args:
            root: Tkinter root window
            timezones: List of tuples (timezone_name, display_label)
                      Default includes major cities
        """
        self.root = root
        self.root.title("🕐 Digital Clock - Multiple Time Zones")
        self.root.geometry("600x500")
        self.root.configure(bg="#1a1a1a")

        # Default timezones
        if timezones is None:
            self.timezones = [
                ("Asia/Ho_Chi_Minh", "🇻🇳 Hà Nội (UTC+7)"),
                ("Asia/Shanghai", "🇨🇳 Bắc Kinh (UTC+8)"),
                ("Asia/Tokyo", "🇯🇵 Tokyo (UTC+9)"),
                ("Asia/Singapore", "🇸🇬 Singapore (UTC+8)"),
                ("America/New_York", "🇺🇸 New York (UTC-5)"),
                ("Europe/London", "🇬🇧 London (UTC+0)"),
            ]
        else:
            self.timezones = timezones

        self.time_labels = []
        self.setup_ui()
        self.update_time()

    def setup_ui(self):
        """Setup user interface"""
        # Title
        title_font = font.Font(family="Helvetica", size=20, weight="bold")
        title_label = tk.Label(
            self.root,
            text="⏰ Digital Clock",
            font=title_font,
            fg="#00ff00",
            bg="#1a1a1a",
        )
        title_label.pack(pady=20)

        # Time zones container
        self.time_frame = tk.Frame(self.root, bg="#1a1a1a")
        self.time_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        # Create labels for each timezone
        for timezone_name, display_label in self.timezones:
            # Label frame
            frame = tk.Frame(self.time_frame, bg="#2a2a2a", relief=tk.SUNKEN, bd=2)
            frame.pack(fill=tk.X, pady=8)

            # City name
            city_font = font.Font(family="Helvetica", size=12, weight="bold")
            city_label = tk.Label(
                frame,
                text=display_label,
                font=city_font,
                fg="#00ff00",
                bg="#2a2a2a",
                anchor="w",
                padx=10,
                pady=5,
            )
            city_label.pack(side=tk.LEFT, padx=10)

            # Time display
            time_font = font.Font(family="Courier New", size=16, weight="bold")
            time_label = tk.Label(
                frame,
                text="00:00:00",
                font=time_font,
                fg="#00ff00",
                bg="#2a2a2a",
                anchor="e",
                padx=10,
                pady=5,
            )
            time_label.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=10)

            # Store references
            self.time_labels.append((timezone_name, time_label))

        # Status bar
        status_frame = tk.Frame(self.root, bg="#2a2a2a", relief=tk.SUNKEN, bd=1)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM)

        status_font = font.Font(family="Helvetica", size=9)
        self.status_label = tk.Label(
            status_frame,
            text="✓ Live updating...",
            font=status_font,
            fg="#00ff00",
            bg="#2a2a2a",
            anchor="w",
            padx=10,
            pady=5,
        )
        self.status_label.pack(fill=tk.X)

    def update_time(self):
        """Update time for all timezones"""
        try:
            # Get current time
            now = datetime.now(pytz.UTC)

            # Update each timezone
            for timezone_name, time_label in self.time_labels:
                tz = pytz.timezone(timezone_name)
                local_time = now.astimezone(tz)
                time_str = local_time.strftime("%H:%M:%S")
                time_label.config(text=time_str)

            # Update status
            update_time = datetime.now().strftime("%H:%M:%S")
            self.status_label.config(text=f"✓ Updated: {update_time}")

        except Exception as e:
            self.status_label.config(text=f"✗ Error: {str(e)}")

        # Schedule next update (every 1000ms = 1 second)
        self.root.after(1000, self.update_time)

    def add_timezone(self, timezone_name: str, display_label: str):
        """
        Add new timezone to display

        Args:
            timezone_name: Pytz timezone name (e.g., 'Asia/Ho_Chi_Minh')
            display_label: Display label (e.g., '🇻🇳 Hà Nội')
        """
        # Create new frame for timezone
        frame = tk.Frame(self.time_frame, bg="#2a2a2a", relief=tk.SUNKEN, bd=2)
        frame.pack(fill=tk.X, pady=8)

        # City name
        city_font = font.Font(family="Helvetica", size=12, weight="bold")
        city_label = tk.Label(
            frame,
            text=display_label,
            font=city_font,
            fg="#00ff00",
            bg="#2a2a2a",
            anchor="w",
            padx=10,
            pady=5,
        )
        city_label.pack(side=tk.LEFT, padx=10)

        # Time display
        time_font = font.Font(family="Courier New", size=16, weight="bold")
        time_label = tk.Label(
            frame,
            text="00:00:00",
            font=time_font,
            fg="#00ff00",
            bg="#2a2a2a",
            anchor="e",
            padx=10,
            pady=5,
        )
        time_label.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=10)

        # Store reference
        self.time_labels.append((timezone_name, time_label))


class DigitalClockConsole:
    """Console-based digital clock"""

    def __init__(self, timezones: List[Tuple[str, str]] = None):
        """
        Initialize console clock

        Args:
            timezones: List of tuples (timezone_name, display_label)
        """
        if timezones is None:
            self.timezones = [
                ("Asia/Ho_Chi_Minh", "🇻🇳 Hà Nội"),
                ("Asia/Shanghai", "🇨🇳 Bắc Kinh"),
                ("Asia/Tokyo", "🇯🇵 Tokyo"),
                ("America/New_York", "🇺🇸 New York"),
                ("Europe/London", "🇬🇧 London"),
                ("Australia/Sydney", "🇦🇺 Sydney"),
            ]
        else:
            self.timezones = timezones

    def display_once(self) -> None:
        """Display time once (no loop)"""
        now = datetime.now(pytz.UTC)

        print("\n" + "=" * 60)
        print("⏰ DIGITAL CLOCK - CURRENT TIME IN MULTIPLE TIME ZONES")
        print("=" * 60)

        for timezone_name, display_label in self.timezones:
            tz = pytz.timezone(timezone_name)
            local_time = now.astimezone(tz)

            # Format: Label | Time | Offset
            time_str = local_time.strftime("%H:%M:%S")
            offset = local_time.strftime("%z")
            offset_formatted = f"{offset[:3]}:{offset[3:]}"

            print(
                f"{display_label:20} | {time_str} | UTC{offset_formatted:>6}"
            )

        print("=" * 60 + "\n")

    def display_live(self, duration: int = 300) -> None:
        """
        Display time with live updates

        Args:
            duration: Duration in seconds to run (default 5 minutes)
        """
        import time

        start_time = time.time()

        try:
            while time.time() - start_time < duration:
                # Clear screen
                import os

                os.system("clear" if os.name == "posix" else "cls")

                # Display
                self.display_once()

                # Wait 1 second
                time.sleep(1)

        except KeyboardInterrupt:
            print("\n⚠️  Stopped by user\n")


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Digital Clock - Multiple Time Zones",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  %(prog)s gui                  # GUI mode
  %(prog)s console              # Console mode (once)
  %(prog)s console --live       # Console mode (live)
  %(prog)s console --duration 60  # Live for 60 seconds
        """,
    )

    parser.add_argument(
        "mode",
        choices=["gui", "console"],
        nargs="?",
        default="gui",
        help="Display mode",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Live update mode (console only)",
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=300,
        help="Duration in seconds for live mode (default: 300)",
    )

    args = parser.parse_args()

    if args.mode == "gui":
        # GUI Mode
        root = tk.Tk()
        clock = DigitalClock(root)
        root.mainloop()

    else:
        # Console Mode
        clock = DigitalClockConsole()

        if args.live:
            clock.display_live(args.duration)
        else:
            clock.display_once()


if __name__ == "__main__":
    main()
