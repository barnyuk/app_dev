#import re
#import threading
import tkinter as tk
#from pathlib import Path
#from tkinter import filedialog, messagebox, scrolledtext, ttk
from tkinter import ttk
#from config.settings import SITPLANES_DIR, OUTPUT_DIR
#from src.authization.authorize import get_token
#from src.core.data_merger import process_job

class Authorize(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('Авторизация')
        self.geometry('300x200')
        self.resizable(False, False)
        self.login_label = ttk.Label(self, text='Логин:')
        self.login_label.pack()
        self.login_entry = ttk.Entry(self, width=40)
        self.login_entry.pack()
        self.password_label = ttk.Label(self, text='Пароль:')
        self.password_label.pack()
        self.password_entry = ttk.Entry(self, show='*', width=40)
        self.password_entry.pack()
        self.confirm_button = ttk.Button(self, text='Войти', command=self._authorize)

    def _authorize(self):
        login = self.login_entry.get().strip()
        password = self.password_entry.get().strip()

        try:
            



Authorize().mainloop()
