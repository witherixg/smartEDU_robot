import json
import os
import webbrowser
from threading import Thread

import requests
import tkinter as tk
from tkinter import filedialog
from tkinter import ttk
from concurrent.futures import ThreadPoolExecutor
from queue import Queue


headers = {}
# const
tag_url = "https://s-file-1.ykt.cbern.com.cn/zxx/ndrs/tags/tch_material_tag.json"
data_urls = "https://s-file-2.ykt.cbern.com.cn/zxx/ndrs/resources/tch_material/version/data_version.json"
book_url_template = "https://r{0}-ndr.ykt.cbern.com.cn/edu_product/esp/assets_document/{1}.pkg/{2}.pdf"

# tree var
BUFFER_SIZE = 1024
thread_num = 64
download_list = []
path = ""


class BookPath:

    def __init__(self, parent: list[str], uuid: str = ""):
        self.paths: list[str] = parent + ([uuid] if not uuid == "" else [])

    def full_path(self) -> str:
        return "/".join(self.paths)

    def __hash__(self):
        return self.full_path().__hash__()

    def __str__(self):
        return self.full_path().__str__()

    def __add__(self, other: str):
        return BookPath(self.paths, other)

    def __len__(self):
        return len(self.paths)

    def __eq__(self, other):
        return self.__str__() == other.__str__()

    def __getitem__(self, item):
        return BookPath(list(self.paths[item]))


class Node:

    def __init__(self, name, uuid, next_uuids, parent_path):
        self.name: str = name
        self.uuid: str = uuid
        self.next_uuids: list[str] = next_uuids
        self.parent_path: BookPath = parent_path

    def __str__(self):
        return f"{self.parent_path} -> {self.name}({self.uuid}): {self.next_uuids}"

    def as_path(self) -> BookPath:
        return self.parent_path + self.uuid


class Book:

    def __init__(self, name, uuid, book_path):
        self.name: str = name
        self.uuid: str = uuid
        self.book_path: BookPath = book_path

    def __str__(self):
        return f"{self.name}({self.uuid}) at {self.book_path}"

    def __hash__(self):
        return self.book_path.__hash__()

    def __eq__(self, other):
        return self.__str__() == other.__str__()


# custom var
node_dict: dict[BookPath, Node] = dict()
book_list: list[Book] = []
book_dict: dict[str, Book] = dict()
root_node: Node
# Progress
current_bytes: int = 0
total_bytes: int = 0

def load_json(file_url: str, is_local: bool = False) -> dict:
    if is_local:
        with open(file_url, "r", encoding="utf-8") as file:
            return json.load(file)
    else:
        return requests.get(file_url, headers=headers).json()


def add_books_and_dirs():
    # dirs
    base_node = load_json(tag_url)["hierarchies"][0]["children"][0]
    global node_dict
    global book_list
    global root_node
    queue: Queue[(dict, BookPath)] = Queue()
    base_path = BookPath([])
    queue.put((base_node, base_path))
    base_id = base_node["tag_id"]
    # node_dict[base_id] = Node(base_node["tag_name"], base_id, base_node["hierarchies"][0]["ext"]["has_next_tag_path"], "")
    while not queue.empty():
        node: dict
        parent: BookPath
        node, parent = queue.get()
        node_id: str = node["tag_id"]
        if node["hierarchies"] is None:
            next_list = []
            next_nodes = []
        else:
            next_nodes = node["hierarchies"][0]["children"]
            next_list = list(map(lambda child: child["tag_id"], next_nodes))

        book_path = parent + node_id
        node_dict[book_path] = Node(node["tag_name"], node_id, next_list, parent)

        for next_node in next_nodes:
            queue.put((next_node, book_path))
    root_node = node_dict[base_path + base_id]

    # books
    part_urls = load_json(data_urls)["urls"].split(',')
    for part_url in part_urls:
        books_json = load_json(part_url)
        for book_json in books_json:
            book_id: str = book_json["id"]
            if len(book_json["tag_paths"]) == 0:
                continue
            book_tag_paths: list[str] = book_json["tag_paths"][0].split('/')
            for i in range(len(book_tag_paths), 1, -1):
                cut_tag_paths = book_tag_paths[1:i]
                if BookPath(cut_tag_paths) in node_dict.keys():
                    book = Book(book_json["title"], book_id, BookPath(cut_tag_paths))
                    book_list.append(book)
                    book_dict[book_id] = book
                    break


def print_nodes():
    queue = Queue()
    queue.put(root_node)

    while not queue.empty():
        node = queue.get()
        print(node)
        for next_uuid in node.next_uuids:
            queue.put(node_dict[node.as_path() + next_uuid])


def get_path_name_list(book: Book) -> list[str]:
    full_path: BookPath = book.book_path
    name_list: list[str] = []
    for i in range(len(full_path)):
        book_path = full_path[0:i + 1]
        name = node_dict[book_path].name
        name_list.append(name)
    return name_list


def websites(s: str):
    website_dict = {
        "Github": "https://github.com/witherixg/smartEDU_robot/",
        "Lanzou": "https://sywt.lanzout.com/b021btj2f"
    }

    def open_website():
        webbrowser.open(website_dict[s])

    return open_website


def show_gui():
    global path
    # Init window
    root = tk.Tk()
    root.tk.call("source", "azure.tcl")
    root.tk.call("set_theme", "light")
    root.geometry("800x500")
    root.title("\u7535\u5B50\u8BFE\u672C\u4E0B\u8F7D\u5668")
    if not os.path.exists("./smartEDU_temp.ico"):
        with open("./smartEDU_temp.ico", "wb+") as icon:
            icon.write(requests.get("https://basic.smartedu.cn/favicon.ico").content)
    root.iconbitmap("./smartEDU_temp.ico")
    root.resizable(width=False, height=False)

    # Vars
    dark_mode_var = tk.BooleanVar(value=False)
    path_var = tk.StringVar(value=os.path.expanduser("~/Desktop/").replace("\\", "/"))
    thread_num_var = tk.StringVar()
    progress_var = tk.IntVar(value=0)

    path = path_var.get()
    if not path[-1] == "/":
        path += "/"
    path.replace("\\", "/")

    selected_book_list = []

    # Functions

    def dark_mode_switcher():
        nonlocal dark_mode_var
        if dark_mode_var.get():
            root.tk.call("set_theme", "dark")
        else:
            root.tk.call("set_theme", "light")

    def path_selector():
        nonlocal path_var
        global path
        path_var.set(filedialog.askdirectory())
        path = path_var.get()
        if not path[-1] == "/":
            path += "/"
        path.replace("\\", "/")


    def on_select(_):
        nonlocal book_list_treeview
        nonlocal selected_book_list
        selected_items = list(map(lambda uuid: book_dict[uuid], filter(lambda uuid: uuid in book_dict.keys(), book_list_treeview.selection())))
        selected_book_list = list(filter(lambda item: item in book_list, selected_items))

    def thread_num_setter():
        nonlocal thread_num_var
        global thread_num
        thread_num = int(thread_num_var.get())

    def setting_writer():
        nonlocal dark_mode_var
        nonlocal path_var
        nonlocal thread_num_var
        nonlocal progress_var
        with open("./smartEDU_robot.cfg", "w") as f:
            f.write(f"{dark_mode_var.get()}\n")
            f.write(f"{path_var.get()}\n")
            f.write(f"{thread_num_var.get()}\n")
            f.write(f"{progress_var.get()}")
            f.close()
        tk.messagebox.showinfo(title="\u7535\u5B50\u8BFE\u672C\u4E0B\u8F7D\u5668",
                               message="\u6210\u529F\u4FDD\u5B58\uFF01")

    def download_all():
        global current_bytes
        global total_bytes
        current_bytes = 0
        total_bytes = 0
        with ThreadPoolExecutor(max_workers=thread_num) as pool:
            pool.map(start, selected_book_list)

        tk.messagebox.showinfo(title="\u7535\u5B50\u8BFE\u672C\u4E0B\u8F7D\u5668",
                               message="\u6210\u529F\u4E0B\u8F7D\uFF01")

    def start(book: Book):
        prepare(book)
        download(book)

    def prepare(book: Book):
        paths = get_path_name_list(book)
        if "" in paths:
            paths.remove("")
        for i in range(len(paths)):
            if not os.path.exists(path + '/'.join(paths[0: i + 1])):
                os.mkdir(path + '/'.join(paths[0: i + 1]))

    def get_response(book: Book) -> requests.Response | None:
        arg_0 = [1, 2, 3]
        arg_2 = ["pdf", book.name]
        for i in arg_0:
            for j in arg_2:
                book_url = book_url_template.format(i, book.uuid, j)
                response = requests.get(book_url, headers=headers, stream=True)
                if not response.content == "":
                    return response

        return None

    def download(book: Book):
        global current_bytes
        global total_bytes
        response = get_response(book)
        # Get file size
        total_bytes += int(response.headers['Content-Length'])
        book_path = f"{path}{'/'.join(get_path_name_list(book))}/{book.name}.pdf"
        with open(book_path, "wb") as f:
            for data in response.iter_content(BUFFER_SIZE):
                f.write(data)
                current_bytes += len(data)
                progress_var.set(current_bytes * 100 / total_bytes)
            f.close()

    def download_file():
        Thread(target=download_all).start()

    notebook = ttk.Notebook(root)
    # Two frames
    main_frame = tk.Frame(root)
    setting_frame = tk.Frame(root)

    # ==================== Main Frame ====================
    book_list_y_scrollbar = ttk.Scrollbar(main_frame)
    book_list_y_scrollbar.pack(side="right", fill="y")
    book_list_treeview = ttk.Treeview(
        main_frame,
        yscrollcommand=book_list_y_scrollbar.set,
        height=10,
        columns="uuid",
        displaycolumns=""
    )
    book_list_treeview.pack(expand=True, fill="both")
    book_list_y_scrollbar.config(command=book_list_treeview.yview)

    book_list_treeview.bind("<<TreeviewSelect>>", on_select)

    # Get the uuid of each dir/book and add it to the tree view
    # dir
    queue = Queue()
    queue.put(root_node)
    while not queue.empty():
        node = queue.get()
        book_list_treeview.insert(
            parent=str(node.parent_path), index="end", iid=node.as_path(), text=node.name
        )
        for next_uuid in node.next_uuids:
            queue.put(node_dict[node.as_path() + next_uuid])

    # book
    for book in book_list:
        book_list_treeview.insert(
            parent=str(book.book_path), index="end", iid=book.uuid, text=book.name
        )

    button = ttk.Button(main_frame, text="\u4E0B\u8F7D", command=download_file)
    button.pack(padx=5, side="right")
    progress = ttk.Progressbar(
        main_frame, value=0, variable=progress_var, mode="determinate"
    )
    progress.pack(padx=20, pady=20, fill="x")
    progress["maximum"] = 100

    # ==================== Main Frame ====================

    # ==================== Setting Frame ====================
    ui_setting_frame = ttk.LabelFrame(setting_frame, text="UI \u8BBE\u7F6E")
    ui_setting_frame.grid(
        row=0, column=0, padx=20, pady=20, sticky="nsew"
    )

    dark_label = tk.Label(ui_setting_frame, text="\u6DF1\u8272\u6A21\u5F0F", width=16, height=1, anchor=tk.W)
    dark_label.grid(row=0, column=0, padx=5, pady=5)
    dark_switch = ttk.Checkbutton(
        ui_setting_frame, text="", style="Switch.TCheckbutton", variable=dark_mode_var,
        command=dark_mode_switcher
    )
    dark_switch.grid(row=0, column=1, padx=5, pady=5)

    download_setting_frame = ttk.LabelFrame(setting_frame, text="\u4E0B\u8F7D\u8BBE\u7F6E")
    download_setting_frame.grid(
        row=1, column=0, padx=20, pady=20, sticky="nsew"
    )

    thread_num_label = tk.Label(download_setting_frame, text="\u7EBF\u7A0B\u6570", width=16, height=1, anchor=tk.W)
    thread_num_label.grid(row=0, column=0, padx=5, pady=5)

    thread_num_spinbox = ttk.Spinbox(
        download_setting_frame, from_=1, to=128, increment=1, textvariable=thread_num_var, command=thread_num_setter
    )
    thread_num_spinbox.set(1)
    thread_num_spinbox.grid(row=0, column=1, padx=5, pady=5)

    path_label = tk.Label(download_setting_frame, text="\u4FDD\u5B58\u8DEF\u5F84", width=16, height=1, anchor=tk.W)
    path_label.grid(row=1, column=0, padx=5, pady=5)

    path_entry = ttk.Entry(download_setting_frame, textvariable=path_var, state="readonly")
    path_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

    path_button = ttk.Button(download_setting_frame, text="\u9009\u62E9...", command=path_selector)
    path_button.grid(row=1, column=2, padx=5, pady=5, sticky="nsew")

    about_frame = ttk.LabelFrame(setting_frame, text="\u76F8\u5173\u9875\u9762")
    about_frame.grid(
        row=3, column=0, padx=20, pady=20, sticky="nsew"
    )

    github_button = ttk.Button(about_frame, text="Github", command=websites("Github"))
    github_button.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")

    lanzou_button = ttk.Button(about_frame, text="\u84DD\u594F\u4E91(\u5BC6\u7801:dzjc)", command=websites("Lanzou"))
    lanzou_button.grid(row=0, column=1, padx=5, pady=5, sticky="nsew")

    save_button = ttk.Button(
        setting_frame, text="\u4FDD\u5B58\u8BBE\u7F6E", style="Accent.TButton", command=setting_writer
    )
    save_button.grid(row=4, column=0, padx=5, pady=5, sticky="nsew")

    # ==================== Setting Frame ====================
    # Get settings if existent
    if os.path.exists("./smartEDU_robot.cfg") and os.path.isfile("./smartEDU_robot.cfg"):
        with open("./smartEDU_robot.cfg", "r") as file:
            if (file.readline().replace("\n", "")) == "True":
                dark_mode_var.set(True)
                dark_mode_switcher()
            path_var.set(file.readline().replace("\n", ""))
            thread_num_var.set(file.readline().replace("\n", ""))
            progress_var.set(int(file.readline().replace("\n", "")))
            file.close()

    # Put frames in tabs
    notebook.add(main_frame, text="\u4E3B\u9875\u9762")
    notebook.add(setting_frame, text="\u8BBE\u7F6E")
    notebook.pack(padx=5, pady=5, fill=tk.BOTH, expand=True)

    root.mainloop()


def main():
    add_books_and_dirs()
    show_gui()


if __name__ == '__main__':
    main()
