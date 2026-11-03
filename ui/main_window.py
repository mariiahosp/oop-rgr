import tkinter as tk
from tkinter import ttk


class MainWindow:
    """Main application window."""

    def __init__(self, root: tk.Tk):
        self.root = root

        self.root.title("C++ Include Analyzer")
        self.root.geometry("1100x700")
        self.root.minsize(700, 450)

        self._create_menu()
        self._create_layout()

    def _create_menu(self):
        """Create the application menu."""

        menu_bar = tk.Menu(self.root)

        file_menu = tk.Menu(menu_bar, tearoff=0)
        file_menu.add_command(label="Open Project...")
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.destroy)

        view_menu = tk.Menu(menu_bar, tearoff=0)
        view_menu.add_command(label="Reset View")

        help_menu = tk.Menu(menu_bar, tearoff=0)
        help_menu.add_command(label="About")

        menu_bar.add_cascade(label="File", menu=file_menu)
        menu_bar.add_cascade(label="View", menu=view_menu)
        menu_bar.add_cascade(label="Help", menu=help_menu)

        self.root.config(menu=menu_bar)

    def _create_layout(self):
        """Create the main window layout."""

        # Project information panel
        self.project_frame = ttk.Frame(self.root, padding=10)
        self.project_frame.pack(fill=tk.X)

        self.project_label = ttk.Label(
            self.project_frame,
            text="Project: No project opened",
            font=("Arial", 11)
        )
        self.project_label.pack(side=tk.LEFT)

        # Main visualization area
        self.viewer_frame = ttk.LabelFrame(
            self.root,
            text="Include Hierarchy",
            padding=5
        )
        self.viewer_frame.pack(
            fill=tk.BOTH,
            expand=True,
            padx=10,
            pady=(0, 10)
        )

        self.canvas = tk.Canvas(
            self.viewer_frame,
            background="white"
        )

        self.vertical_scrollbar = ttk.Scrollbar(
            self.viewer_frame,
            orient=tk.VERTICAL,
            command=self.canvas.yview
        )

        self.horizontal_scrollbar = ttk.Scrollbar(
            self.viewer_frame,
            orient=tk.HORIZONTAL,
            command=self.canvas.xview
        )

        self.canvas.configure(
            yscrollcommand=self.vertical_scrollbar.set,
            xscrollcommand=self.horizontal_scrollbar.set
        )

        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.vertical_scrollbar.grid(row=0, column=1, sticky="ns")
        self.horizontal_scrollbar.grid(row=1, column=0, sticky="ew")

        self.viewer_frame.rowconfigure(0, weight=1)
        self.viewer_frame.columnconfigure(0, weight=1)

        # Status bar
        self.status_label = ttk.Label(
            self.root,
            text="Ready",
            relief=tk.SUNKEN,
            anchor=tk.W,
            padding=5
        )
        self.status_label.pack(fill=tk.X)
