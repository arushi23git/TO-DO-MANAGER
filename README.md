A fully featured desktop To-Do List Manager built using Python, Tkinter, and tkcalendar. Designed with clean UI/UX, smart sorting, date picker support, task filtering, exporting, and more.

🚀 Features ✔️ Core Features

Add tasks with:

Title / Description

Priority: High, Medium, Low

Due date (with Date Picker)

Edit existing tasks

Mark tasks as completed

Delete tasks

Automatically saves data to todo_data.json

🎨 UI / UX Improvements

Modernized Tkinter UI using ttk themes

Priority-based color coding:

🔴 High priority

🟠 Medium priority

🟢 Low priority

Completed tasks shown in gray

Overdue tasks highlighted in red

Responsive layout compatible with all screen sizes

🔍 Productivity Tools

Search bar (real-time filtering)

Filter tasks:

All

Pending

Completed

By priority

Sort order:

Pending → Completed

Priority (High → Low)

Due soonest first

Created date

📅 Date Picker

Modern calendar widget for selecting due dates

Automatically validates date format

Falls back to normal text input if tkcalendar is not installed

📦 Export Features

Export individual tasks as:

.txt

.json

⌨️ Keyboard Shortcuts Shortcut Action Ctrl + N Focus “New Task” Ctrl + E Edit selected task Delete Delete selected task Ctrl + Q Quit app 📸 Screenshots (optional)

Add screenshots after running your app.

🛠️ Installation & Setup

Clone the Repository git clone https://github.com//.git cd

Create Virtual Environment (Recommended) python -m venv venv source venv/bin/activate # Mac/Linux venv\Scripts\activate # Windows

Install Requirements pip install tkcalendar

(Only one dependency is needed — Tkinter is included with Python.)

Run the Application python todo_app.py
📂 Project Structure 📁 your-project/ │── todo_app.py # Main application │── todo_data.json # Auto-generated saved tasks │── README.md # Documentation

🧩 Dependencies Package Purpose tkcalendar Provides the date picker widget (DateEntry)

Install using:

pip install tkcalendar

📘 How It Works Data Storage

All tasks are stored locally inside todo_data.json

Includes fields:

id

text

priority

due_date

created

completed

deleted

Sorting Logic

Tasks are sorted based on:

Completion status (Pending → Completed)

Priority (High → Medium → Low)

Due date (nearest first)

Creation date

✨ Future Enhancements

You can extend the project further:

Add categories/tags

Add notifications/reminders

Add sub-tasks

Export all tasks together

Add theme switcher (dark/light mode)

Convert to EXE using PyInstaller

If you want, I can implement any of these for you.

🤝 Contributing

Feel free to open issues or pull requests to improve this project.

📄 License

This project is open-source and you may modify and distribute it as needed.

❤️ Acknowledgements

Built using Python + Tkinter

Calendar UI powered by tkcalendar

Developer: Arushi Sengupta (arushi23git)
