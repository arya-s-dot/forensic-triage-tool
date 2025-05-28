import re
import csv
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
from datetime import datetime

chat_data = []

# Regex pattern for Android export: 14/05/24, 9:23 pm - Name: Message
chat_line_re = re.compile(r"^(\d{1,2}/\d{1,2}/\d{2}), (\d{1,2}:\d{2}) (am|pm) - (.*?): (.*)$")

def parse_chat_lines(lines):
    parsed = []
    for line in lines:
        match = chat_line_re.match(line.strip())
        if match:
            date, time, meridian, sender, message = match.groups()
            try:
                dt = datetime.strptime(f"{date} {time} {meridian}", "%d/%m/%y %I:%M %p")
            except ValueError:
                continue
            parsed.append({
                'datetime': dt,
                'date': dt.date().isoformat(),
                'time': dt.time().isoformat(timespec='minutes'),
                'sender': sender,
                'message': message
            })
    return parsed

def load_chat_file():
    filepath = filedialog.askopenfilename(filetypes=[("Text files", "*.txt")])
    if not filepath:
        return
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    global chat_data
    chat_data = parse_chat_lines(lines)
    populate_table(chat_data)
    update_summary()

def populate_table(data):
    for row in tree.get_children():
        tree.delete(row)
    for row in data:
        tree.insert('', 'end', values=(row['date'], row['time'], row['sender'], row['message']))

def export_to_csv():
    if not chat_data:
        messagebox.showinfo("Export", "No data to export.")
        return
    path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
    if not path:
        return
    with open(path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(['Date', 'Time', 'Sender', 'Message'])
        for row in chat_data:
            writer.writerow([row['date'], row['time'], row['sender'], row['message']])
    messagebox.showinfo("Export", f"Exported to {path}")

def update_summary():
    summary_label.config(text=f"Total messages: {len(chat_data)}")

# --- GUI ---
root = tk.Tk()
root.title("WhatsApp Chat Viewer");
root.geometry("900x600")

btn_frame = tk.Frame(root)
btn_frame.pack(pady=10)

tk.Button(btn_frame, text="Load Chat (.txt)", command=load_chat_file).pack(side=tk.LEFT, padx=5)
tk.Button(btn_frame, text="Export to CSV", command=export_to_csv).pack(side=tk.LEFT, padx=5)

summary_label = tk.Label(root, text="Total messages: 0")
summary_label.pack()

cols = ('Date', 'Time', 'Sender', 'Message')
tree = ttk.Treeview(root, columns=cols, show='headings', height=25)
for col in cols:
    tree.heading(col, text=col)
    tree.column(col, anchor='w', width=150 if col != 'Message' else 450)
tree.pack(fill='both', expand=True)

root.mainloop()
