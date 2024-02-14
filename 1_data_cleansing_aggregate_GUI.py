import tkinter as tk
from tkinter import filedialog
from data_cleansing_aggregate import load_and_process_data

# Create a function to handle file selection
def select_csv_file():
    file_path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])
    if file_path:
        load_and_process_data(file_path)
        print(f"fp: {file_path}")



# Create the main application window
root = tk.Tk()
root.title("CSV File Selector")


# Create a label and place it above the button
label = tk.Label(root, text="Show Peak & Light Day Pattern")
label.pack(pady=(20, 0))  # Adding some padding for better spacing


# Create a button to open the file dialog
select_button = tk.Button(root, text="Select .csv File", command=select_csv_file)
select_button.pack(pady=20)

tk.Label(root, text=f"suggest combined_data.csv or <data>_edit.csv").pack()
tk.Label(root, text=f"result create: prepared_electric_load_data.csv").pack()


# Start the Tkinter main loop
root.mainloop()

