import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from analysis.dependency_graph import DependencyGraph
from analysis.include_analyzer import IncludeAnalyzer
from models.project import Project
from viewer.graph_viewer import GraphViewer


class MainWindow:
    def __init__(self, root: tk.Tk):
        self.root = root

        self.root.title("Аналізатор #include-ієрархії C++")
        self.root.geometry("1100x700")
        self.root.minsize(700, 450)

        self.project: Project | None = None
        self._modifier = "Command" if root.tk.call("tk", "windowingsystem") == "aqua" else "Control"

        self._create_menu()
        self._create_layout()
        self._bind_shortcuts()

    def _create_menu(self):
        shortcut = "Cmd" if self._modifier == "Command" else "Ctrl"
        menu_bar = tk.Menu(self.root)

        file_menu = tk.Menu(menu_bar, tearoff=0)
        file_menu.add_command(
            label="Відкрити...",
            accelerator=f"{shortcut}+O",
            command=self._open_main_file,
        )
        file_menu.add_command(
            label="Відкрити папку проекту...",
            accelerator=f"{shortcut}+Shift+O",
            command=self._open_project_folder,
        )
        file_menu.add_separator()
        file_menu.add_command(label="Вихід", command=self.root.destroy)

        view_menu = tk.Menu(menu_bar, tearoff=0)
        view_menu.add_command(label="Оновити", accelerator="F5", command=self._reload)
        view_menu.add_command(label="На початок схеми", command=self._reset_view)

        help_menu = tk.Menu(menu_bar, tearoff=0)
        help_menu.add_command(label="Позначення", command=self._show_legend)
        help_menu.add_command(label="Про програму", command=self._show_about)

        menu_bar.add_cascade(label="Файл", menu=file_menu)
        menu_bar.add_cascade(label="Вигляд", menu=view_menu)
        menu_bar.add_cascade(label="Довідка", menu=help_menu)

        self.root.config(menu=menu_bar)

    def _bind_shortcuts(self):
        self.root.bind(f"<{self._modifier}-o>", lambda _: self._open_main_file())
        self.root.bind(f"<{self._modifier}-O>", lambda _: self._open_project_folder())
        self.root.bind("<F5>", lambda _: self._reload())

    def _create_layout(self):
        self.project_frame = ttk.Frame(self.root, padding=10)
        self.project_frame.pack(fill=tk.X)

        self.project_label = ttk.Label(
            self.project_frame, text="Проект не відкрито", font=("Arial", 11)
        )
        self.project_label.pack(side=tk.LEFT)

        self.viewer_frame = ttk.LabelFrame(
            self.root, text="#include-ієрархія", padding=5
        )
        self.viewer_frame.pack(fill=tk.BOTH, expand=True, padx=18, pady=(8, 16))

        self.canvas = tk.Canvas(self.viewer_frame, background="white", highlightthickness=0)

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
            self.root,
            text="Оберіть «Файл → Відкрити...», щоб побудувати схему",
            relief=tk.SUNKEN,
            anchor=tk.W,
            padding=5,
        )
        self.status_label.pack(fill=tk.X)

        self.viewer = GraphViewer(self.canvas)

    def _reset_view(self) -> None:
        self.viewer.reset_view()

    def _reload(self) -> None:
        if self.project is None:
            return
        main_file = str(self.project.main_file) if self.project.main_file else None
        self._load_project(str(self.project.root_path), main_file)

    def _show_legend(self) -> None:
        messagebox.showinfo(
            "Позначення",
            "Білий блок — файл вихідного тексту (*.cpp, *.rc)\n"
            "Блакитний блок — заголовочний файл проекту (*.h)\n"
            "Зелений блок — системні заголовочні файли\n"
            "Стопка блоків — група системних файлів\n"
            "Червоний пунктир — файл не знайдено в папці проекту\n\n"
            "Стрілка #include веде від файлу, що підключається,\n"
            "до файлу, який його підключає.\n"
            "Червона пунктирна стрілка — циклічне підключення.",
        )

    def _show_about(self) -> None:
        messagebox.showinfo(
            "Про програму",
            "Аналізатор #include-ієрархії C++\n\n"
            "Розрахунково-графічна робота\n"
            "Об’єктно-орієнтоване програмування\n\n"
            "Господінова Марія",
        )

    def _open_project_folder(self):
        folder_path = filedialog.askdirectory(title="Оберіть папку проекту C++")

        if not folder_path:
            return

        self._load_project(folder_path)

    def _open_main_file(self):
        file_path = filedialog.askopenfilename(
            title="Оберіть головний файл проекту",
            filetypes=[
                ("Файли C++", "*.cpp *.h *.rc"),
                ("Усі файли", "*.*"),
            ],
        )

        if not file_path:
            return

        self._load_project(str(Path(file_path).parent), main_file=file_path)

    def _load_project(self, folder_path: str, main_file: str | None = None):
        try:
            project = Project(folder_path, main_file)

            if not project.root_path.is_dir():
                messagebox.showerror("Помилка", "Обраної папки не існує.")
                return

            source_files = project.get_source_files()

            if not source_files:
                messagebox.showwarning(
                    "Порожній проект", "У папці немає файлів *.cpp, *.h або *.rc."
                )
                return

            sources = IncludeAnalyzer().analyze(project)
            graph = DependencyGraph(sources, project.main_file)
            self.project = project
            self.viewer.show(graph)

            title = f"Проект: {project.name}"
            if project.main_file is not None:
                title += f"  |  Головний файл: {project.main_file.name}"
            self.project_label.config(text=title)

            status = (
                f"{project.root_path}  |  Файлів: {len(source_files)}  |  "
                f"Зв'язків #include: {len(graph.edges)}  |  Рівнів: {graph.level_count}"
            )
            if graph.cycle_count:
                status += f"  |  Циклічних підключень: {graph.cycle_count}"
            self.status_label.config(text=status)

        except OSError as error:
            messagebox.showerror("Помилка", f"Не вдалося відкрити проект:\n{error}")
