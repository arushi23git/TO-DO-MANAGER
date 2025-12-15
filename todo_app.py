"""
To-Do List Manager with Date Picker (tkcalendar DateEntry)
- Uses tkcalendar.DateEntry when available for picking due dates.
- Falls back to plain Entry if tkcalendar is not installed.
- Other features retained: ID generation, overdue highlighting, export, edit, keyboard shortcuts.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime, date
import json
import os
from pathlib import Path

# Try to import DateEntry from tkcalendar; if not available, set a flag to use fallback Entry
try:
    from tkcalendar import DateEntry
    TKCALENDAR_AVAILABLE = True
except Exception:
    TKCALENDAR_AVAILABLE = False

APP_NAME = "To-Do List Manager"
DATA_FILE = Path.cwd() / "todo_data.json"   # Use project folder so PyCharm runs find it

def next_id(tasks):
    """Return next integer ID based on max existing id (handles deleted tasks)."""
    if not tasks:
        return 1
    try:
        max_id = max(int(t.get("id", 0)) for t in tasks)
    except ValueError:
        max_id = 0
    return max_id + 1

class TodoApp:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_NAME)
        self.root.geometry("900x650")
        self.root.minsize(800, 500)

        # data
        self.data_file = DATA_FILE
        self.tasks = self.load_tasks()

        # UI state vars
        self.priority_var = tk.StringVar(value="Medium")
        self.filter_var = tk.StringVar(value="All")
        self.search_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Ready")

        self.setup_style()
        self.setup_ui()
        self.refresh_task_list()
        self.setup_bindings()

    def setup_style(self):
        style = ttk.Style(self.root)
        try:
            style.theme_use('clam')
        except Exception:
            pass
        style.configure("Treeview.Heading", font=('Segoe UI', 10, 'bold'))
        style.configure("TButton", padding=6)
        style.configure("TLabel", font=('Segoe UI', 10))
        style.configure("Header.TLabel", font=('Segoe UI', 16, 'bold'))

    def setup_ui(self):
        main = ttk.Frame(self.root, padding=12)
        main.grid(sticky=(tk.N, tk.S, tk.E, tk.W))
        self.root.rowconfigure(0, weight=1)
        self.root.columnconfigure(0, weight=1)

        # Header
        header = ttk.Label(main, text="📝 " + APP_NAME, style="Header.TLabel")
        header.grid(row=0, column=0, columnspan=4, pady=(0, 12), sticky=tk.W)

        # Add task area
        add_frame = ttk.LabelFrame(main, text="Add New Task", padding=10)
        add_frame.grid(row=1, column=0, columnspan=4, sticky=(tk.W, tk.E), pady=(0, 12))
        add_frame.columnconfigure(1, weight=1)

        ttk.Label(add_frame, text="Task:").grid(row=0, column=0, padx=6, pady=4, sticky=tk.W)
        self.task_entry = ttk.Entry(add_frame)
        self.task_entry.grid(row=0, column=1, columnspan=2, sticky=(tk.W, tk.E), padx=(0,6))
        self.task_entry.bind('<Return>', lambda e: self.add_task())

        ttk.Label(add_frame, text="Priority:").grid(row=0, column=3, padx=6, sticky=tk.W)
        priority_combo = ttk.Combobox(add_frame, textvariable=self.priority_var,
                                      values=["High", "Medium", "Low"], width=10, state="readonly")
        priority_combo.grid(row=0, column=4, padx=(0,6))

        ttk.Label(add_frame, text="Due Date:").grid(row=1, column=0, padx=6, pady=(6,0), sticky=tk.W)

        # Due date widget: DateEntry if tkcalendar available, else plain Entry
        if TKCALENDAR_AVAILABLE:
            # DateEntry uses date_pattern 'y-mm-dd' or 'yyyy-mm-dd' depending on tkcalendar version.
            # Use 'yyyy-mm-dd' to be explicit if supported, otherwise 'y-mm-dd' works on older versions.
            try:
                self.due_date_widget = DateEntry(add_frame, width=16, date_pattern='yyyy-mm-dd')
            except TypeError:
                # Fallback if the DateEntry version doesn't support 'yyyy-mm-dd' pattern name
                self.due_date_widget = DateEntry(add_frame, width=16, date_pattern='y-mm-dd')
        else:
            self.due_date_widget = ttk.Entry(add_frame, width=20)
            self.due_date_widget.insert(0, "YYYY-MM-DD (optional)")
            self.due_date_widget.bind("<FocusIn>", self._clear_date_placeholder)

        self.due_date_widget.grid(row=1, column=1, padx=(0,6), pady=(6,0), sticky=tk.W)

        add_btn = ttk.Button(add_frame, text="Add Task", command=self.add_task)
        add_btn.grid(row=1, column=4, padx=6, pady=(6,0), sticky=tk.E)

        # Left filter/search pane
        left = ttk.Frame(main)
        left.grid(row=2, column=0, sticky=(tk.N, tk.S, tk.W), padx=(0,12))
        left.columnconfigure(0, weight=1)

        ttk.Label(left, text="Filter:", font=('Segoe UI', 10, 'bold')).pack(anchor=tk.W)
        filters = ["All", "Pending", "Completed", "High Priority", "Medium Priority", "Low Priority"]
        for f in filters:
            ttk.Radiobutton(left, text=f, variable=self.filter_var, value=f,
                            command=self.refresh_task_list).pack(anchor=tk.W, pady=2)

        ttk.Label(left, text="Search:", font=('Segoe UI', 10, 'bold')).pack(anchor=tk.W, pady=(10,0))
        search_entry = ttk.Entry(left, textvariable=self.search_var)
        search_entry.pack(fill=tk.X, pady=(2,6))
        self.search_var.trace_add("write", lambda *_: self.refresh_task_list())

        self.stats_label = ttk.Label(left, text="", font=('Segoe UI', 9))
        self.stats_label.pack(anchor=tk.W, pady=(8, 0))

        # Task list
        list_frame = ttk.LabelFrame(main, text="Tasks", padding=6)
        list_frame.grid(row=2, column=1, columnspan=3, sticky=(tk.N, tk.S, tk.E, tk.W))
        main.rowconfigure(2, weight=1)
        main.columnconfigure(3, weight=1)
        list_frame.rowconfigure(0, weight=1)
        list_frame.columnconfigure(0, weight=1)

        columns = ("ID", "Priority", "Task", "Due Date", "Days Left", "Status", "Created")
        self.tree = ttk.Treeview(list_frame, columns=columns, show="headings", selectmode='browse', height=18)

        for col in columns:
            self.tree.heading(col, text=col)
        self.tree.column("ID", width=50, anchor=tk.CENTER)
        self.tree.column("Priority", width=90, anchor=tk.CENTER)
        self.tree.column("Task", width=350, anchor=tk.W)
        self.tree.column("Due Date", width=110, anchor=tk.CENTER)
        self.tree.column("Days Left", width=90, anchor=tk.CENTER)
        self.tree.column("Status", width=90, anchor=tk.CENTER)
        self.tree.column("Created", width=110, anchor=tk.CENTER)

        vsb = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))
        vsb.grid(row=0, column=1, sticky=(tk.N, tk.S))

        # Buttons row
        btn_frame = ttk.Frame(main)
        btn_frame.grid(row=3, column=0, columnspan=4, pady=10, sticky=tk.W)

        ttk.Button(btn_frame, text="Mark Complete", command=self.toggle_complete).pack(side=tk.LEFT, padx=6)
        ttk.Button(btn_frame, text="Edit Task", command=self.edit_task).pack(side=tk.LEFT, padx=6)
        ttk.Button(btn_frame, text="Delete Task", command=self.delete_task).pack(side=tk.LEFT, padx=6)
        ttk.Button(btn_frame, text="Clear Completed", command=self.clear_completed).pack(side=tk.LEFT, padx=6)
        ttk.Button(btn_frame, text="Export Task...", command=self.export_task).pack(side=tk.LEFT, padx=6)

        # Status bar
        status_bar = ttk.Label(main, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.grid(row=4, column=0, columnspan=4, sticky=(tk.E, tk.W), pady=(6,0))

        # tree tags styling
        self.tree.tag_configure('completed', foreground='gray')
        self.tree.tag_configure('overdue', foreground='red')
        self.tree.tag_configure('high_priority', foreground='red', font=('Segoe UI', 10, 'bold'))
        self.tree.tag_configure('medium_priority', foreground='orange')
        self.tree.tag_configure('low_priority', foreground='green')

    def setup_bindings(self):
        self.tree.bind('<Double-1>', lambda e: self.on_tree_double_click())
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        # keyboard shortcuts
        self.root.bind_all('<Control-n>', lambda e: self.task_entry.focus_set())
        self.root.bind_all('<Control-N>', lambda e: self.task_entry.focus_set())
        self.root.bind_all('<Control-e>', lambda e: self.edit_task())
        self.root.bind_all('<Delete>', lambda e: self.delete_task())
        self.root.bind_all('<Control-q>', lambda e: self.on_close())

    def _clear_date_placeholder(self, event):
        widget = event.widget
        if isinstance(widget, ttk.Entry):
            if widget.get().startswith("YYYY"):
                widget.delete(0, tk.END)

    def validate_date(self, s):
        if not s:
            return None
        try:
            d = datetime.strptime(s, "%Y-%m-%d").date()
            return d
        except ValueError:
            return "INVALID"

    def add_task(self):
        text = self.task_entry.get().strip()
        if not text:
            messagebox.showwarning("Warning", "Please enter a task description.")
            return

        # read date from DateEntry or Entry
        if TKCALENDAR_AVAILABLE and isinstance(self.due_date_widget, DateEntry):
            # DateEntry returns string in the configured date_pattern
            due_raw = self.due_date_widget.get().strip()
            # Some DateEntry allow empty string; interpret as None
            if due_raw == '':
                due = None
            else:
                valid = self.validate_date(due_raw)
                if valid == "INVALID":
                    messagebox.showerror("Error", "Invalid date format. Use YYYY-MM-DD.")
                    return
                due = valid.isoformat()
        else:
            due_raw = self.due_date_widget.get().strip()
            if due_raw.startswith("YYYY") or not due_raw:
                due = None
            else:
                valid = self.validate_date(due_raw)
                if valid == "INVALID":
                    messagebox.showerror("Error", "Invalid date format. Use YYYY-MM-DD.")
                    return
                due = valid.isoformat()

        task = {
            "id": str(next_id(self.tasks)),
            "text": text,
            "priority": self.priority_var.get(),
            "due_date": due,
            "completed": False,
            "created": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "deleted": False
        }

        self.tasks.append(task)
        self.save_tasks()
        self.refresh_task_list()

        self.task_entry.delete(0, tk.END)
        # reset due date widget to blank or placeholder
        if TKCALENDAR_AVAILABLE and isinstance(self.due_date_widget, DateEntry):
            # set to blank by setting to today's date, then clear.
            try:
                self.due_date_widget.set_date('')
            except Exception:
                # not all versions allow empty set; set to today to provide clear field
                self.due_date_widget.set_date(date.today())
        else:
            self.due_date_widget.delete(0, tk.END)
            self.due_date_widget.insert(0, "YYYY-MM-DD (optional)")

        self.status_var.set(f"Task added: {text}")

    def get_selected_task(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Warning", "Please select a task.")
            return None
        values = self.tree.item(sel[0], 'values')
        task_id = values[0]
        for t in self.tasks:
            if t.get('id') == str(task_id) and not t.get('deleted', False):
                return t
        return None

    def toggle_complete(self):
        t = self.get_selected_task()
        if not t:
            return
        t['completed'] = not t.get('completed', False)
        self.save_tasks()
        self.refresh_task_list()
        self.status_var.set(f"Task {'completed' if t['completed'] else 'marked pending'}: {t['text']}")

    def edit_task(self):
        t = self.get_selected_task()
        if not t:
            return

        dlg = tk.Toplevel(self.root)
        dlg.title("Edit Task")
        dlg.transient(self.root)
        dlg.grab_set()
        dlg.geometry("460x220")
        dlg.resizable(False, False)

        ttk.Label(dlg, text="Task:").grid(row=0, column=0, padx=10, pady=8, sticky=tk.W)
        e_task = ttk.Entry(dlg, width=60)
        e_task.grid(row=0, column=1, padx=10, pady=8)
        e_task.insert(0, t['text'])

        ttk.Label(dlg, text="Priority:").grid(row=1, column=0, padx=10, pady=8, sticky=tk.W)
        pvar = tk.StringVar(value=t['priority'])
        pcombo = ttk.Combobox(dlg, textvariable=pvar, values=["High", "Medium", "Low"], state="readonly", width=12)
        pcombo.grid(row=1, column=1, padx=10, pady=8, sticky=tk.W)

        ttk.Label(dlg, text="Due Date:").grid(row=2, column=0, padx=10, pady=8, sticky=tk.W)

        # Use DateEntry in edit dialog if available, else Entry
        if TKCALENDAR_AVAILABLE:
            try:
                d_entry = DateEntry(dlg, width=16, date_pattern='yyyy-mm-dd')
            except TypeError:
                d_entry = DateEntry(dlg, width=16, date_pattern='y-mm-dd')
            # populate existing due date if present
            if t.get('due_date'):
                try:
                    d_entry.set_date(t.get('due_date'))
                except Exception:
                    # ignore if set_date fails; DateEntry will display its default
                    pass
        else:
            d_entry = ttk.Entry(dlg, width=20)
            if t.get('due_date'):
                d_entry.insert(0, t.get('due_date'))

        d_entry.grid(row=2, column=1, padx=10, pady=8, sticky=tk.W)

        def save():
            new_text = e_task.get().strip()
            if not new_text:
                messagebox.showwarning("Warning", "Task cannot be empty.")
                return
            # read date from DateEntry or Entry
            if TKCALENDAR_AVAILABLE and isinstance(d_entry, DateEntry):
                raw = d_entry.get().strip()
                if raw == '':
                    new_due_iso = None
                else:
                    valid = self.validate_date(raw)
                    if valid == "INVALID":
                        messagebox.showerror("Error", "Invalid date format. Use YYYY-MM-DD.")
                        return
                    new_due_iso = valid.isoformat()
            else:
                raw = d_entry.get().strip()
                if raw:
                    valid = self.validate_date(raw)
                    if valid == "INVALID":
                        messagebox.showerror("Error", "Invalid date format. Use YYYY-MM-DD.")
                        return
                    new_due_iso = valid.isoformat()
                else:
                    new_due_iso = None

            t['text'] = new_text
            t['priority'] = pvar.get()
            t['due_date'] = new_due_iso
            self.save_tasks()
            self.refresh_task_list()
            self.status_var.set("Task updated")
            dlg.destroy()

        btn_frame = ttk.Frame(dlg)
        btn_frame.grid(row=3, column=0, columnspan=2, pady=10)
        ttk.Button(btn_frame, text="Save", command=save).pack(side=tk.LEFT, padx=6)
        ttk.Button(btn_frame, text="Cancel", command=dlg.destroy).pack(side=tk.LEFT, padx=6)

    def delete_task(self):
        t = self.get_selected_task()
        if not t:
            return
        if messagebox.askyesno("Delete", f"Delete task: {t['text']}?"):
            t['deleted'] = True
            self.save_tasks()
            self.refresh_task_list()
            self.status_var.set("Task deleted")

    def clear_completed(self):
        comp = [t for t in self.tasks if t.get('completed') and not t.get('deleted', False)]
        if not comp:
            messagebox.showinfo("Info", "No completed tasks to clear.")
            return
        if messagebox.askyesno("Confirm", f"Clear {len(comp)} completed task(s)?"):
            for t in comp:
                t['deleted'] = True
            self.save_tasks()
            self.refresh_task_list()
            self.status_var.set(f"Cleared {len(comp)} completed tasks")

    def on_tree_double_click(self):
        # Edit on double click
        self.edit_task()

    def refresh_task_list(self):
        for it in self.tree.get_children():
            self.tree.delete(it)

        f = self.filter_var.get()
        s = self.search_var.get().lower().strip()

        visible = []
        for t in self.tasks:
            if t.get('deleted', False):
                continue
            if f == "Pending" and t.get('completed'):
                continue
            if f == "Completed" and not t.get('completed'):
                continue
            if f.endswith("Priority") and t.get('priority') != f.split()[0]:
                continue
            if s and s not in t.get('text', '').lower():
                continue
            visible.append(t)

        pri_order = {"High": 0, "Medium": 1, "Low": 2}
        def sort_key(x):
            due = x.get('due_date') or "9999-12-31"
            return (x.get('completed', False), pri_order.get(x.get('priority'), 1), due, x.get('created',''))
        visible.sort(key=sort_key)

        today = date.today()
        for t in visible:
            due = t.get('due_date')
            if due:
                try:
                    due_date = datetime.strptime(due, "%Y-%m-%d").date()
                    delta = (due_date - today).days
                    days_left = f"{delta} day(s)" if delta >= 0 else f"{abs(delta)} day(s) overdue"
                except Exception:
                    days_left = "Invalid date"
                    due_date = None
            else:
                days_left = "N/A"
                due_date = None

            status = "✓ Done" if t.get('completed') else "Pending"
            created = t.get('created', '').split()[0]
            tags = []
            if t.get('completed'):
                tags.append('completed')
            else:
                if t.get('priority') == 'High':
                    tags.append('high_priority')
                elif t.get('priority') == 'Medium':
                    tags.append('medium_priority')
                else:
                    tags.append('low_priority')
                if due_date and due_date < today:
                    tags.append('overdue')

            self.tree.insert('', tk.END, values=(
                t.get('id'), t.get('priority'), t.get('text'), due or "No due date", days_left, status, created
            ), tags=tags)

        total = len([x for x in self.tasks if not x.get('deleted', False)])
        completed = len([x for x in self.tasks if x.get('completed') and not x.get('deleted', False)])
        pending = total - completed
        self.stats_label.config(text=f"Total: {total} | Pending: {pending} | Completed: {completed}")

    def load_tasks(self):
        if self.data_file.exists():
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                messagebox.showwarning("Warning", "Could not read data file; starting with empty list.")
                return []
        return []

    def save_tasks(self):
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self.tasks, f, indent=2, ensure_ascii=False)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save tasks: {e}")

    def export_task(self):
        t = self.get_selected_task()
        if not t:
            return

        path = filedialog.asksaveasfilename(defaultextension=".txt",
                                            filetypes=[("Text files", "*.txt"), ("JSON", "*.json")],
                                            title="Export Task")
        if not path:
            return
        try:
            if path.lower().endswith('.json'):
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(t, f, indent=2, ensure_ascii=False)
            else:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(f"Task ID: {t.get('id')}\n")
                    f.write(f"Task: {t.get('text')}\n")
                    f.write(f"Priority: {t.get('priority')}\n")
                    f.write(f"Due Date: {t.get('due_date') or 'No due date'}\n")
                    f.write(f"Status: {'Done' if t.get('completed') else 'Pending'}\n")
                    f.write(f"Created: {t.get('created')}\n")
            messagebox.showinfo("Exported", f"Task exported to {path}")
            self.status_var.set(f"Exported task {t.get('id')}")
        except Exception as e:
            messagebox.showerror("Error", f"Export failed: {e}")

    def on_close(self):
        if messagebox.askyesno("Quit", "Do you want to save and exit?"):
            self.save_tasks()
            self.root.destroy()

def main():
    root = tk.Tk()
    app = TodoApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
