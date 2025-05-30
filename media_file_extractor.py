import subprocess
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime
from pathlib import Pathh
import os
import re
from PIL import Image, ImageTk
import csv
import mimetypes
import tempfile
import webbrowser

summary_label = None
preview_window = None


def run_adb_query(uri):
    try:
        result = subprocess.run(
            ['adb', 'shell', 'content', 'query', '--uri', uri,
             '--projection', '_data:_display_name:date_added', '--user', '0'],
            capture_output=True, text=True, encoding='utf-8', timeout=30
        )
        return result.stdout if result.returncode == 0 else ""
    except Exception as e:
        messagebox.showerror("ADB Error", str(e))
        return ""


def parse_output(output):
    rows = []
    for line in output.strip().splitlines():
        line = line.strip()
        if not line.startswith("Row:"):
            continue
        match = re.search(r'Row:\s*\d+\s+(.*)', line)
        if not match:
            continue
        fields = match.group(1).split(', ')
        row = {}
        for field in fields:
            if '=' in field:
                k, v = field.split('=', 1)
                row[k.strip()] = v.strip()
        if row.get('_data'):
            rows.append(row)
    return rows


def filter_by_date(rows, start_date_str, end_date_str):
    try:
        if not start_date_str or not end_date_str:
            return rows
        start_ts = int(datetime.strptime(start_date_str, '%Y-%m-%d').timestamp())
        end_ts = int(datetime.strptime(end_date_str, '%Y-%m-%d').timestamp())
        return [row for row in rows if start_ts <= int(row.get('date_added', '0')) <= end_ts]
    except:
        return rows


def filter_by_folder(rows, folder_name):
    if not folder_name or folder_name == "All":
        return rows
    return [row for row in rows if folder_name.lower() in row.get('_data', '').lower()]


def pull_file(path, destination):
    if not path:
        return None
    dest_dir = Path(destination)
    dest_dir.mkdir(parents=True, exist_ok=True)
    filename = os.path.basename(path)
    local_path = dest_dir / filename
    result = subprocess.run(['adb', 'pull', path, str(local_path)], capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error pulling {path}: {result.stderr.strip()}")
        return None
    return str(local_path)


def export_selected():
    selected = tree.selection()
    if not selected:
        messagebox.showwarning("No Selection", "Select at least one media to export.")
        return

    folder = filedialog.askdirectory(title="Choose Export Directory")
    if not folder:
        return

    for item_id in selected:
        row = tree.item(item_id)['values']
        remote_path = row[0]
        local_path = pull_file(remote_path, folder)
        if local_path:
            print(f"Pulled: {local_path}")
    messagebox.showinfo("Export Complete", f"Exported {len(selected)} files to {folder}")


def export_csv():
    selected = tree.selection()
    if not selected:
        messagebox.showwarning("No Selection", "Select at least one media row to export to CSV.")
        return

    file = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[["CSV Files", "*.csv"]])
    if not file:
        return

    with open(file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['_data', '_display_name', 'date_added'])
        for item_id in selected:
            writer.writerow(tree.item(item_id)['values'])

    messagebox.showinfo("CSV Export", f"Saved CSV to {file}")


def update_summary(event=None):
    if summary_label:
        total = len(tree.get_children())
        selected = len(tree.selection())
        summary_label.config(text=f"Media Files: {selected} selected of {total} total")


def preview_selected(event):
    global preview_window

    selected = tree.focus()
    if not selected:
        return
    values = tree.item(selected)['values']
    if not values:
        return
    path = values[0]
    mime_type, _ = mimetypes.guess_type(path)
    temp_dir = Path("temp_preview")
    temp_dir.mkdir(exist_ok=True)
    pulled = pull_file(path, str(temp_dir))
    if not pulled or not os.path.isfile(pulled):
        return

    if preview_window and preview_window.winfo_exists():
        preview_window.destroy()

    preview_window = tk.Toplevel(root)
    preview_window.title("Preview")
    preview_window.geometry("320x300")

    if mime_type and (mime_type.startswith('video') or mime_type.startswith('audio')):
        webbrowser.open(pulled)
        preview_window.destroy()
    else:
        try:
            img = Image.open(pulled)
            img.thumbnail((300, 300))
            img_tk = ImageTk.PhotoImage(img)
            lbl = tk.Label(preview_window, image=img_tk)
            lbl.image = img_tk
            lbl.pack()
        except:
            messagebox.showerror("Preview Error", "Image preview failed.")


def select_all():
    for item in tree.get_children():
        tree.selection_add(item)
    update_summary()


def deselect_all():
    tree.selection_remove(tree.selection())
    update_summary()


def load_data():
    uri = type_var.get()
    output = run_adb_query(uri)
    if not output:
        messagebox.showerror("ADB Query Failed", "No output received from ADB.")
        return

    print("[DEBUG] ADB output preview:\n", output[:300])

    tree.delete(*tree.get_children())

    data = parse_output(output)

    start_date_str = start_entry.get()
    end_date_str = end_entry.get()
    data = filter_by_date(data, start_date_str, end_date_str)

    # Populate dynamic folder filter
    folders = sorted(set(Path(row['_data']).parts[-2] for row in data if '_data' in row))
    folder_dropdown['values'] = ['All'] + folders
    folder_dropdown.current(0)

    selected_folder = folder_var.get()
    data = filter_by_folder(data, selected_folder)

    if not data:
        messagebox.showwarning("No Data Found", "No media found from device in the specified filters.")
        return

    for item in data:
        try:
            timestamp = int(item.get('date_added', '0'))
            date_str = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
        except:
            date_str = ''
        tree.insert('', tk.END, values=(item.get('_data', ''), item.get('_display_name', ''), date_str))
    update_summary()

    print(f"[DEBUG] Loaded {len(data)} records into table")


# GUI Setup
root = tk.Tk()
root.title("ADB Media Extractor")
root.geometry("1300x750")

frame = ttk.Frame(root)
frame.pack(fill=tk.BOTH, expand=True)

columns = ('_data', '_display_name', 'date_added')
tree = ttk.Treeview(frame, columns=columns, show='headings', selectmode='extended')
for col in columns:
    tree.heading(col, text=col)
    tree.column(col, width=400 if col == '_data' else 200)
tree.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)

tree.bind("<<TreeviewSelect>>", update_summary)
tree.bind("<<TreeviewSelect>>", preview_selected)

scroll = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=tree.yview)
tree.configure(yscrollcommand=scroll.set)
scroll.pack(fill=tk.Y, side=tk.LEFT)

preview_label = tk.Label(root)
preview_label.pack(pady=5)

summary_label = tk.Label(root, text="Media Files: 0 selected of 0 total")
summary_label.pack(pady=2)

filter_frame = tk.Frame(root)
filter_frame.pack(pady=5)

tk.Label(filter_frame, text="Start Date (YYYY-MM-DD):").pack(side=tk.LEFT, padx=5)
start_entry = tk.Entry(filter_frame, width=12)
start_entry.pack(side=tk.LEFT)

tk.Label(filter_frame, text="End Date (YYYY-MM-DD):").pack(side=tk.LEFT, padx=5)
end_entry = tk.Entry(filter_frame, width=12)
end_entry.pack(side=tk.LEFT)

tk.Label(filter_frame, text="Folder Filter:").pack(side=tk.LEFT, padx=5)
folder_var = tk.StringVar()
folder_dropdown = ttk.Combobox(filter_frame, textvariable=folder_var)
folder_dropdown['values'] = ["All"]
folder_dropdown.current(0)
folder_dropdown.pack(side=tk.LEFT, padx=5)

tk.Label(filter_frame, text="Media Type:").pack(side=tk.LEFT, padx=5)
type_var = tk.StringVar(value='content://media/external/images/media')
type_dropdown = ttk.Combobox(filter_frame, textvariable=type_var, width=40)
type_dropdown['values'] = [
    'content://media/external/images/media',
    'content://media/external/video/media',
    'content://media/external/audio/media'
]
type_dropdown.pack(side=tk.LEFT, padx=5)

button_frame = tk.Frame(root)
button_frame.pack(pady=10)

tk.Button(button_frame, text="Load Media", command=load_data).pack(side=tk.LEFT, padx=5)
tk.Button(button_frame, text="Select All", command=select_all).pack(side=tk.LEFT, padx=5)
tk.Button(button_frame, text="Deselect All", command=deselect_all).pack(side=tk.LEFT, padx=5)
tk.Button(button_frame, text="Export Selected", command=export_selected).pack(side=tk.LEFT, padx=5)
tk.Button(button_frame, text="Export CSV", command=export_csv).pack(side=tk.LEFT, padx=5)

root.mainloop()
