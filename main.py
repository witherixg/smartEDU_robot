import requests
import os
import tkinter as tk
from tkinter import filedialog
from tkinter import ttk
from concurrent.futures import ThreadPoolExecutor, as_completed

headers = {
}

tag_url = "https://s-file-1.ykt.cbern.com.cn/zxx/ndrs/tags/tch_material_tag.json"
data_urls = "https://s-file-2.ykt.cbern.com.cn/zxx/ndrs/resources/tch_material/version/data_version.json"
url = "https://r{0}-ndr.ykt.cbern.com.cn/edu_product/esp/assets_document/{1}.pkg/{2}.pdf"
urls = requests.get(data_urls, headers=headers).json()["urls"].split(",")
book_folders = []
books = []
uuid_dict = {}
book_uuid_dict = {}
uuid_tree = []
uuid_chosen_dict = {}
BUFFER_SIZE = 1024
thread_num = 64
download_list = []
path = ""


class BookFolder:
    def __init__(self, path_, uuids):
        self.path = path_
        self.uuids = uuids


class Book:
    def __init__(self, folder, uuid, name):
        self.folder = folder
        self.uuid = uuid
        self.name = name


def add_books():
    json = requests.get(tag_url, headers=headers).json()["hierarchies"][0]
    global uuid_tree
    for f1 in json["children"]:
        f1_id, f1_k, f1_v = f1["tag_id"], f1["tag_name"], f1["hierarchies"][0]
        uuid_dict[f1_id] = f1_k
        f2_list = []
        for f2 in f1_v["children"]:
            f2_id, f2_k, f2_v = f2["tag_id"], f2["tag_name"], f2["hierarchies"][0]
            uuid_dict[f2_id] = f2_k
            f3_list = []
            for f3 in f2_v["children"]:
                f3_id, f3_k, f3_v = f3["tag_id"], f3["tag_name"], f3["hierarchies"][0]
                uuid_dict[f3_id] = f3_k
                f4_list = []
                for f4 in f3_v["children"]:
                    if f2_k == "高中":
                        f4_id, f4_k, f4_v = f4["tag_id"], f4["tag_name"], f4["hierarchies"]
                        uuid_dict[f4_id] = f4_k
                        book_folders.append(
                            BookFolder(f"{f1_k}/{f2_k}/{f3_k}/{f4_k}/", sorted((f1_id, f2_id, f3_id, f4_id))))
                        f4_list.append(f4_id)
                    else:
                        f4_id, f4_k, f4_v = f4["tag_id"], f4["tag_name"], f4["hierarchies"][0]
                        uuid_dict[f4_id] = f4_k
                        f5_list = []
                        for f5 in f4_v["children"]:
                            f5_id, f5_k, f5_v = f5["tag_id"], f5["tag_name"], f5["hierarchies"]
                            uuid_dict[f5_id] = f5_k
                            book_folders.append(
                                BookFolder(f"{f1_k}/{f2_k}/{f3_k}/{f4_k}/{f5_k}/",
                                           sorted((f1_id, f2_id, f3_id, f4_id, f5_id))))
                            f5_list.append(f5_id)
                        f4_list.append({f4_id: f5_list})
                f3_list.append({f3_id: f4_list})
            f2_list.append({f2_id: f3_list})
        uuid_tree.append({f1_id: f2_list})


def get_books():
    for u in urls:
        json = requests.get(u, headers=headers).json()
        for book in json:
            book_uuid = book["id"]
            temp_tag_list = book["tag_list"]
            book_tag_list = []
            book_name = book["title"]
            for tag in temp_tag_list:
                if "册" in tag["tag_name"] \
                        or "修" in tag["tag_name"] \
                        or tag["tag_name"] == "教材" \
                        or tag["tag_name"] == "高中年级":
                    pass
                else:
                    book_tag_list.append(tag["tag_id"])
            book_tag_list.sort()
            for folder in book_folders:
                if folder.uuids == book_tag_list:
                    books.append(Book(folder, book_uuid, book_name))
                    book_uuid_dict[book_uuid] = book_name
    for k in book_uuid_dict.keys():
        uuid_dict[k] = book_uuid_dict[k]
    for k in uuid_dict.keys():
        uuid_chosen_dict[k] = 0


# Deprecated
def print_book_folders():
    for element in book_folders:
        print(f"{id(element)}: ({element.uuids}) at {element.path}")


# Deprecated
def print_books():
    for element in books:
        print(f"{element.uuid}: {element.name} at {element.folder.path}")


def download_all():
    with ThreadPoolExecutor(max_workers=thread_num) as pool:
        download_books = []
        for uuid in download_list:
            for book in books:
                if book.uuid == uuid:
                    download_books.append(book)
                    break
        pool.map(start, download_books)


def start(book):
    prepare(book)
    download(book)


def prepare(book):
    paths = book.folder.path.split("/")
    if "" in paths:
        paths.remove("")
    for i in range(len(paths)):
        if not os.path.exists(path + "/".join(paths[0: i + 1])):
            try:
                os.mkdir(path + "/".join(paths[0: i + 1]))
            except Exception:
                return


def get_response(book):
    arg_0 = [1, 2, 3]
    arg_2 = ["pdf", book.name]
    for i in arg_0:
        for j in arg_2:
            book_url = url.format(i, book.uuid, j)
            response = requests.get(book_url, headers=headers, stream=True)
            if not response.content == "":
                return response


def download(book):
    response = get_response(book)
    book_path = f"{path}{book.folder.path}{book.name}.pdf"
    with open(book_path, "wb") as f:
        for data in response.iter_content(BUFFER_SIZE):
            f.write(data)
        f.close()


def exist_match(small_list: list, large_list: list) -> bool:
    if len(small_list) > len(large_list):
        return False

    for element in small_list:
        if element not in large_list:
            return False

    return True


def show_gui():
    global path
    # Init window
    root = tk.Tk()
    root.tk.call("source", "azure.tcl")
    root.tk.call("set_theme", "light")
    root.geometry("800x500")
    root.title("电子课本下载器")
    with open("./smartEDU_temp.ico", "wb+") as icon:
        icon.write(requests.get("https://basic.smartedu.cn/favicon.ico").content)
    root.iconbitmap("./smartEDU_temp.ico")
    if os.path.exists("./smartEDU_temp.ico"):
        pass
    root.resizable(width=False, height=False)

    # Vars
    dark_mode_var = tk.BooleanVar(value=False)
    path_var = tk.StringVar(value=os.path.join(os.path.expanduser("~"), 'Desktop').replace("\\", "/"))
    thread_num_var = tk.StringVar()
    download_directly_var = tk.BooleanVar(value=False)
    progress_var = tk.IntVar(value=0)

    path = path_var.get()
    if not path[-1] == "/":
        path += "/"
    path.replace("\\", "/")

    # Functions
    def color_resetter(s):
        nonlocal book_list_treeview
        n = book_list_treeview.get_children(s)
        for uuid in n:
            book_list_treeview.tag_configure(uuid, background=get_color(dark_mode_var, uuid_chosen_dict[uuid]))
            color_resetter((uuid,))

    def dark_mode_switcher():
        nonlocal dark_mode_var
        if dark_mode_var.get():
            root.tk.call("set_theme", "dark")
        else:
            root.tk.call("set_theme", "light")
        color_resetter(None)

    def path_selector():
        nonlocal path_var
        global path
        path_var.set(filedialog.askdirectory())
        path = path_var.get()
        if not path[-1] == "/":
            path += "/"
        path.replace("\\", "/")

    def get_color(dark_mode: tk.BooleanVar, status_number):
        if dark_mode.get():
            if status_number == 1:
                return "yellow"
            elif status_number == 2:
                return "orange"
            else:
                return "#333333"
        else:
            if status_number == 1:
                return "#00FFFF"
            elif status_number == 2:
                return "blue"
            else:
                return "white"

    def check_mode_changer(arg):
        nonlocal book_list_treeview
        if download_directly_var.get():
            uuid = book_list_treeview.selection()[0]
            if uuid not in book_uuid_dict.keys():
                return
            download_list.append(uuid)
            download_all()
            download_list.remove(uuid)
        ss = book_list_treeview.selection()
        if arg in uuid_dict.keys():
            ss = (arg,)
        uuid = ss[0]
        if not book_list_treeview.get_children(ss):
            # Change color
            if uuid_chosen_dict[uuid] == 2:
                uuid_chosen_dict[uuid] = 0
                if uuid in download_list:
                    download_list.remove(uuid)
                book_list_treeview.tag_configure(uuid, background=get_color(dark_mode_var, uuid_chosen_dict[uuid]))
            else:
                uuid_chosen_dict[uuid] = 2
                if uuid not in download_list:
                    download_list.append(uuid)
                book_list_treeview.tag_configure(uuid, background=get_color(dark_mode_var, uuid_chosen_dict[uuid]))
            book_list_treeview.parent(ss)
            while ss:
                ss = book_list_treeview.parent(ss)
                c = book_list_treeview.get_children(ss)
                status = 0  # 0 -> Nothing chosen; 1 -> Something chosen; 2 -> Everything chosen.
                for e in c:
                    if uuid_chosen_dict[e] == 2:
                        status += 2
                    elif uuid_chosen_dict[e] == 1:
                        status += 1
                if status == 0:
                    uuid_chosen_dict[ss] = 0
                    book_list_treeview.tag_configure(ss, background=get_color(dark_mode_var, 0))
                elif 0 < status < 2 * len(c):
                    uuid_chosen_dict[ss] = 1
                    book_list_treeview.tag_configure(ss, background=get_color(dark_mode_var, 1))
                elif status == 2 * len(c):
                    uuid_chosen_dict[ss] = 2
                    book_list_treeview.tag_configure(ss, background=get_color(dark_mode_var, 2))

    def thread_num_setter():
        nonlocal thread_num_var
        global thread_num
        try:
            thread_num = int(thread_num_var.get())
        except Exception:
            thread_num_var.set(1)

    def setting_writer():
        nonlocal dark_mode_var
        nonlocal path_var
        nonlocal thread_num_var
        nonlocal download_directly_var
        nonlocal progress_var
        with open("./smartEDU_robot.cfg", "w") as f:
            f.write(f"{dark_mode_var.get()}\n")
            f.write(f"{path_var.get()}\n")
            f.write(f"{thread_num_var.get()}\n")
            f.write(f"{download_directly_var.get()}\n")
            f.write(f"{progress_var.get()}")
            f.close()
        tk.messagebox.showinfo(title="\u7535\u5B50\u8BFE\u672C\u4E0B\u8F7D\u5668",
                               message="\u6210\u529F\u4FDD\u5B58\uFF01")

    def reset_color():
        temp = download_list.copy()
        for i in temp:
            check_mode_changer(i)

    def download_file():
        download_all()
        tk.messagebox.showinfo(title="\u7535\u5B50\u8BFE\u672C\u4E0B\u8F7D\u5668",
                               message="\u6210\u529F\u4E0B\u8F7D\uFF01")
        reset_color()

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

    book_list_treeview.bind("<<TreeviewSelect>>", check_mode_changer)
    # Get the uuid of each book and add it to the tree view
    for f1 in uuid_tree:
        f1_k = [k for k in f1.keys()][0]
        f1_v = f1[f1_k]
        book_list_treeview.insert(
            parent="", index="end", iid=f1_k, text=uuid_dict.get(f1_k), values=f1_k, tags=f1_k
        )
        for f2 in f1_v:
            f2_k = [k for k in f2.keys()][0]
            f2_v = f2[f2_k]
            book_list_treeview.insert(
                parent=f1_k, index="end", iid=f2_k, text=uuid_dict.get(f2_k), values=f2_k, tags=f2_k
            )
            for f3 in f2_v:
                f3_k = [k for k in f3.keys()][0]
                f3_v = f3[f3_k]
                book_list_treeview.insert(
                    parent=f2_k, index="end", iid=f3_k, text=uuid_dict.get(f3_k), values=f3_k, tags=f3_k
                )
                for f4 in f3_v:
                    if uuid_dict.get(f2_k) == "高中":
                        book_list_treeview.insert(
                            parent=f3_k, index="end", iid=f4, text=uuid_dict.get(f4), values=f4, tags=f4
                        )
                        for b in books:
                            total_uuid = [b.uuid] + b.folder.uuids
                            if exist_match([f1_k, f2_k, f3_k, f4], total_uuid):
                                book_list_treeview.insert(
                                    parent=f4, index="end", iid=b.uuid, text=b.name, values=b.uuid, tags=b.uuid
                                )

                    else:
                        f4_k = [k for k in f4.keys()][0]
                        f4_v = f4[f4_k]
                        book_list_treeview.insert(
                            parent=f3_k, index="end", iid=f4_k, text=uuid_dict.get(f4_k), values=f4_k, tags=f4_k
                        )
                        for f5 in f4_v:
                            book_list_treeview.insert(
                                parent=f4_k, index="end", iid=f5, text=uuid_dict.get(f5), values=f5, tags=f5
                            )
                            for b in books:
                                total_uuid = [b.uuid] + b.folder.uuids
                                if exist_match([f1_k, f2_k, f3_k, f4_k, f5], total_uuid):
                                    book_list_treeview.insert(
                                        parent=f5, index="end", iid=b.uuid, text=b.name, values=b.uuid, tags=b.uuid
                                    )

    download_directly_label = tk.Label(main_frame, text="\u76F4\u63A5\u4E0B\u8F7D", height=1, anchor=tk.W)
    download_directly_label.pack(padx=5, side="left")
    download_directly_switch = ttk.Checkbutton(
        main_frame, text="", style="Switch.TCheckbutton", variable=download_directly_var
    )
    download_directly_switch.pack(side="left")
    button = ttk.Button(main_frame, text="\u4E0B\u8F7D", command=download_file)
    button.pack(padx=5, side="right")
    progress = ttk.Progressbar(
        main_frame, value=0, variable=progress_var, mode="determinate"
    )
    progress.pack(padx=20, pady=20, fill="x")

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

    save_button = ttk.Button(
        setting_frame, text="\u4FDD\u5B58\u8BBE\u7F6E", style="Accent.TButton", command=setting_writer
    )
    save_button.grid(row=3, column=0, padx=5, pady=5, sticky="nsew")

    # ==================== Setting Frame ====================
    # Get settings if existent
    if os.path.exists("./smartEDU_robot.cfg"):
        if os.path.isfile("./smartEDU_robot.cfg"):
            with open("./smartEDU_robot.cfg", "r") as file:
                if (file.readline().replace("\n", "")) == "True":
                    dark_mode_var.set(True)
                    dark_mode_switcher()
                path_var.set(file.readline().replace("\n", ""))
                thread_num_var.set(file.readline().replace("\n", ""))
                download_directly_var.set((file.readline().replace("\n", "")) == "True")
                progress_var.set(int(file.readline().replace("\n", "")))
                file.close()

    # Put frames in tabs
    notebook.add(main_frame, text="\u4E3B\u9875\u9762")
    notebook.add(setting_frame, text="\u8BBE\u7F6E")
    notebook.pack(padx=5, pady=5, fill=tk.BOTH, expand=True)

    root.mainloop()


def main():
    add_books()
    get_books()
    show_gui()


if __name__ == '__main__':
    main()
