import tkinter as tk
from tkinter import ttk
from tkinter import filedialog, messagebox
from models.project import Project
from pathlib import Path
from analysis.include_analyzer import IncludeAnalyzer
from analysis.dependency_graph import DependencyGraph
from viewer.tree_viewer import TreeViewer


class MainWindow:
    def __init__(self, root: tk.Tk):
        self.root = root

        self.root.title("C++ Include Analyzer")
        self.root.geometry("1100x700")
        self.root.minsize(700, 450)

        self.project = None

        self._create_menu()
        self._create_layout()

    def _create_menu(self):

        menu_bar = tk.Menu(self.root)

        file_menu = tk.Menu(menu_bar, tearoff=0)
        file_menu.add_command(
            label="Open Project Folder...", command=self._open_project_folder
        )

        file_menu.add_command(label="Open Main File...", command=self._open_main_file)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.destroy)

        view_menu = tk.Menu(menu_bar, tearoff=0)
        view_menu.add_command(label="Reset View", command=self._reset_view)

        help_menu = tk.Menu(menu_bar, tearoff=0)
        help_menu.add_command(label="About", command=self._show_about)

        menu_bar.add_cascade(label="File", menu=file_menu)
        menu_bar.add_cascade(label="View", menu=view_menu)
        menu_bar.add_cascade(label="Help", menu=help_menu)

        self.root.config(menu=menu_bar)

    def _create_layout(self):
        self.project_frame = ttk.Frame(self.root, padding=10)
        self.project_frame.pack(fill=tk.X)

        self.project_label = ttk.Label(
            self.project_frame, text="Project: No project opened", font=("Arial", 11)
        )
        self.project_label.pack(side=tk.LEFT)

        self.viewer_frame = ttk.LabelFrame(
            self.root, text="Include Hierarchy", padding=5
        )
        self.viewer_frame.pack(fill=tk.BOTH, expand=True, padx=18, pady=(8, 16))

        self.canvas = tk.Canvas(self.viewer_frame, background="white")

        self.vertical_scrollbar = ttk.Scrollbar(
            self.viewer_frame, orient=tk.VERTICAL, command=self.canvas.yview
        )

        self.horizontal_scrollbar = ttk.Scrollbar(
            self.viewer_frame, orient=tk.HORIZONTAL, command=self.canvas.xview
        )

        self.canvas.configure(
            yscrollcommand=self.vertical_scrollbar.set,
            xscrollcommand=self.horizontal_scrollbar.set,
        )

        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.vertical_scrollbar.grid(row=0, column=1, sticky="ns")
        self.horizontal_scrollbar.grid(row=1, column=0, sticky="ew")

        self.viewer_frame.rowconfigure(0, weight=1)
        self.viewer_frame.columnconfigure(0, weight=1)

        self.status_label = ttk.Label(
            self.root, text="Ready", relief=tk.SUNKEN, anchor=tk.W, padding=5
        )
        self.status_label.pack(fill=tk.X)

        self.viewer = TreeViewer(self.canvas)

    def _reset_view(self) -> None:
        self.viewer.reset_view()

    def _show_about(self) -> None:
        messagebox.showinfo(
            "About",
            "C++ Include Analyzer\n\n"
            "Розрахунково-графічна робота\n"
            "Об’єктно-орієнтоване програмування\n\n"
            "Господінова Марія",
        )

    def _open_project_folder(self):
        folder_path = filedialog.askdirectory(title="Select C++ Project Folder")

        if not folder_path:
            return

        self._load_project(folder_path)

    def _open_main_file(self):
        file_path = filedialog.askopenfilename(
            title="Select Main C++ File",
            filetypes=[
                ("C++ source files", "*.cpp"),
                ("All supported files", "*.cpp *.h *.rc"),
                ("All files", "*.*"),
            ],
        )

        if not file_path:
            return

        self._load_project(str(Path(file_path).parent), main_file=file_path)

    def _load_project(self, folder_path: str, main_file: str | None = None):
        try:
            project = Project(folder_path, main_file)

            if not project.root_path.is_dir():
                messagebox.showerror("Error", "Selected project folder does not exist.")
                return

            source_files = project.get_source_files()

            if not source_files:
                messagebox.showwarning(
                    "Empty Project", "No supported C++ files were found."
                )
                return

            self.project = project

            sources = IncludeAnalyzer().analyze(project)
            graph = DependencyGraph(sources, project.main_file)
            include_count = sum(len(source.includes) for source in sources)
            self.viewer.show(graph)

            self.project_label.config(
                text=f"Project: {project.name} | Files: {len(source_files)}"
            )

            self.status_label.config(
                text=f"Opened: {project.root_path} | Includes: {include_count}"
            )

        except OSError as error:
            messagebox.showerror("Project Error", f"Could not open project:\n{error}")
