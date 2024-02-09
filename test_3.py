import tkinter as tk
from tkinter import filedialog
import os

def select_directory(files_dir):
    directory_path = filedialog.askdirectory(initialdir=os.getcwd(), title="Select Directory")
    if directory_path:
        files_dir.set(directory_path)

# Create the main window
root = tk.Tk()
root.title("Directory Selection")

# Create a label and entry widget to display selected directory
tk.Label(root, text="Selected Directory:").pack()
files_dir = tk.StringVar()
tk.Entry(root, textvariable=files_dir, state='readonly').pack()

# Create a button to open file dialog for directory selection
tk.Button(root, text="Select Directory", command=lambda: select_directory(files_dir)).pack()

root.mainloop()
