import os
import re
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk

from config.settings import SITPLANES_DIR, OUTPUT_DIR, root_path
from src.authization.authorize import get_token, user_data
from src.core.data_merger import process_job

OPERATORS = ('A1', 'BEST', 'BE_CLOUD')

icon_path = root_path / 'icons' /'icon.ico'

class AuthorizeDialog(tk.Tk):
    def __init__(self):
        super().__init__()
        if os.path.exists(icon_path):
            self.iconbitmap(icon_path)
        self.resizable(False, False)
        self.title('Aвторизация')
        self.geometry('300x200')
        ttk.Label(self, text='Логин:').pack()
        self.login_entry = ttk.Entry(self, width=55)
        self.login_entry.pack()
        ttk.Label(self, text='Пароль:').pack()
        self.password_entry = ttk.Entry(self, show='*', width=55)
        self.password_entry.pack()
        self.button_enter = ttk.Button(text='Войти', command=self._authorize)
        self.button_enter.pack()

    def _authorize(self):
        username = self.login_entry.get().strip()
        password = self.password_entry.get().strip()

        if not username or not password:
            messagebox.showwarning('Некорректный ввод','Введите логин и пароль')
            return 

        self._auth_busy(True)

        threading.Thread(target=self._auth_worker, args=(username,password), 
                         daemon=True).start()

    def _auth_worker(self, username, password):
        try:
            get_token(username, password)
        except Exception as e:
            self.after(0, lambda: self._auth_failed())
            return

        self.after(0, lambda: self._auth_success(username, password))

    def _auth_failed(self):
        self._auth_busy(False)
        messagebox.showerror('Ошибка авторизации', 'Неверный логин или пароль')

    def _auth_success(self, username, password):
        user_data['username'] = username
        user_data['password'] = password

        self.destroy()
        ProtocolApp().mainloop()


    def _auth_busy(self, busy:bool):
        state = 'disabled' if busy else 'normal'

        self.button_enter.configure(state=state, text='Подождите...' if busy else 'Войти')

class ProtocolApp(tk.Tk):
    def __init__(self):
        super().__init__()
        if os.path.exists(icon_path):
                    self.iconbitmap(icon_path)
        self.title('Генератор протоколов ЭМИ РЧ')
        self.resizable(False, False)
        # --- Пути к папкам ---
        self.sitplan_dir = Path(SITPLANES_DIR)
        self.output_dir = Path(OUTPUT_DIR)

        # Поле выбора папки sitpalnes
        ttk.Label(self, text='Папка ситпланов:').grid(
            row=0, column=0, sticky='w', padx=10, pady=6)
        self.sitplan_entry = ttk.Entry(self, width=55)
        self.sitplan_entry.grid(row=0, column=1, sticky='we', padx=10, pady=6)
        self.sitplan_entry.insert(0, str(self.sitplan_dir))
        self.sitplan_browse = ttk.Button(
            self, text='Обзор...',
            command=self._browse_sitplan)
        self.sitplan_browse.grid(row=0, column=2, padx=10, pady=6)

        # Поле выбора папки для сохранения документов
        ttk.Label(self, text='Папка для сохранения документов:').grid(
            row=1, column=0, sticky='w', padx=10, pady=6)
        self.output_entry = ttk.Entry(self, width=55)
        self.output_entry.grid(row=1, column=1, sticky='we', padx=10, pady=6)
        self.output_entry.insert(0, str(self.output_dir))
        self.output_browse = ttk.Button(
            self, text='Обзор...',
            command=self._browse_output)
        self.output_browse.grid(row=1, column=2, padx=10, pady=6)

        # --- Поля ввода номеров БС ---
        self.entries = {}
        for i, op in enumerate(OPERATORS):
            row = i + 2
            ttk.Label(self, text=f'БС оператора {op}:').grid(
                row=row, column=0, sticky='w', padx=10, pady=6)
            entry = ttk.Entry(self, width=55)
            entry.grid(row=row, column=1, sticky='we', padx=10, pady=6)
            entry.bind('<Return>', lambda _e: self.on_run())
            self.entries[op] = entry

        # --- Поле начального номера протокола ---
        proto_row = len(OPERATORS) + 2
        ttk.Label(self, text='Начальный номер протокола:').grid(
            row=proto_row, column=0, sticky='w', padx=10, pady=6)
        self.protocol_number_entry = ttk.Entry(self, width=55)
        self.protocol_number_entry.grid(
            row=proto_row, column=1, sticky='we', padx=10, pady=6)
        self.protocol_number_entry.insert(0, '1')

        # --- Поля дат (необязательные) ---
        # Дата протокола подставляется в шаблон по ключу {{ДАТАВОРД}},
        # дата испытаний — по ключу {{ДАТА}}. Если поле пустое,
        # используются значения по умолчанию (как и раньше).
        date_row = proto_row + 1
        ttk.Label(self, text='Дата протокола (ДД.ММ.ГГГГ):').grid(
            row=date_row, column=0, sticky='w', padx=10, pady=6)
        self.protocol_date_entry = ttk.Entry(self, width=55)
        self.protocol_date_entry.grid(
            row=date_row, column=1, sticky='we', padx=10, pady=6)

        test_date_row = proto_row + 2
        ttk.Label(self, text='Дата испытаний (ДД.ММ.ГГГГ):').grid(
            row=test_date_row, column=0, sticky='w', padx=10, pady=6)
        self.test_date_entry = ttk.Entry(self, width=55)
        self.test_date_entry.grid(
            row=test_date_row, column=1, sticky='we', padx=10, pady=6)

        # Кнопка запуска
        self.run_button = ttk.Button(
            self, text='Сформировать протоколы', command=self.on_run)
        self.run_button.grid(
            row=proto_row + 3, column=0, columnspan=3, pady=10)

        # Прогресс
        self.progress = ttk.Progressbar(self, mode='determinate')
        self.progress.grid(
            row=proto_row + 4, column=0, columnspan=3,
            sticky='we', padx=10)

        # Журнал
        self.log = scrolledtext.ScrolledText(
            self, width=75, height=14, state='disabled')
        self.log.grid(
            row=proto_row + 5, column=0, columnspan=3, padx=10, pady=8)

        self.entries[OPERATORS[0]].focus_set()

    def _browse_sitplan(self):
        """Open folder dialog for selecting the sitpalnes directory."""
        folder = filedialog.askdirectory(
            title='Выберите папку с ситпланами',
            initialdir=str(self.sitplan_dir),
        )
        if folder:
            self.sitplan_dir = Path(folder)
            self.sitplan_entry.delete(0, tk.END)
            self.sitplan_entry.insert(0, str(self.sitplan_dir))

    def _browse_output(self):
        """Open folder dialog for selecting the output directory."""
        folder = filedialog.askdirectory(
            title='Выберите папку для сохранения документов',
            initialdir=str(self.output_dir),
        )
        if folder:
            self.output_dir = Path(folder)
            self.output_entry.delete(0, tk.END)
            self.output_entry.insert(0, str(self.output_dir))

    @staticmethod
    def parse_bsns(raw: str) -> list:
        """Разбивает ввод на номера БС; номера — только цифры."""
        numbers = list(map(str, raw.split()))
        for n in numbers:
            if not n.isdigit():
                raise ValueError(f'"{n}" — не номер БС. Вводите только цифры через пробел.')
        return numbers

    def on_run(self):
        try:
            jobs = [(op, bsn)
                    for op, entry in self.entries.items()
                    for bsn in self.parse_bsns(entry.get())]
        except ValueError as e:
            messagebox.showerror('Некорректный ввод', str(e))
            return

        if not jobs:
            messagebox.showinfo('Нет данных', 'Введите хотя бы один номер БС.')
            return

        # Parse initial protocol number
        raw_proto = self.protocol_number_entry.get().strip()
        if not raw_proto:
            initial_protocol_number = 1
        else:
            if not raw_proto.isdigit():
                messagebox.showerror(
                    'Некорректный ввод',
                    'Начальный номер протокола должен быть числом.')
                return
            initial_protocol_number = int(raw_proto)

        # Parse optional dates (если пусто — оставляем значения по умолчанию)
        raw_protocol_date = self.protocol_date_entry.get().strip()
        raw_test_date = self.test_date_entry.get().strip()
        for label, value in (('Дата протокола', raw_protocol_date),
                             ('Дата испытаний', raw_test_date)):
            if value and not re.fullmatch(r'\d{2}\.\d{2}\.\d{4}', value):
                messagebox.showerror(
                    'Некорректный ввод',
                    f'{label} должна быть в формате ДД.ММ.ГГГГ.')
                return

        self.run_button.configure(state='disabled')
        self.progress.configure(maximum=len(jobs), value=0)
        self._append_log(f'Старт: {len(jobs)} БС ('
                         + ', '.join(f'{op}: {sum(1 for o, _ in jobs if o == op)}'
                                     for op in OPERATORS)
                         + ')')
        threading.Thread(
            target=self._worker,
            args=(jobs, initial_protocol_number,
                  raw_protocol_date or None, raw_test_date or None),
            daemon=True,
        ).start()

    def _worker(self, jobs, initial_protocol_number,
                protocol_date=None, test_date=None):
        try:
            token = get_token()
        except Exception as e:
            self._log(f'ERR получение токена — {e}')
            self.after(0, self._finish)
            return

        for i, (op, bsn) in enumerate(jobs, start=1):
            protocol_number = initial_protocol_number + i - 1
            try:
                process_job(
                    op, bsn, token,
                    protocol_number=protocol_number,
                    sitplan_dir=self.sitplan_dir,
                    output_dir=self.output_dir,
                    word_date=protocol_date,
                    date=test_date,
                )
                self._log(
                    f'OK  {op} / БС {bsn} — протокол № {protocol_number} '
                    f'сформирован')
            except Exception as e:
                self._log(f'ERR {op} / БС {bsn} — {e}')
            self.after(0, lambda v=i: self.progress.configure(value=v))
        self.after(0, self._finish)

    def _finish(self):
        self.run_button.configure(state='normal')
        self._append_log('Готово.')

    def _log(self, message):
        """Потокобезопасный вывод в журнал (вызов из worker-потока)."""
        self.after(0, lambda m=message: self._append_log(m))

    def _append_log(self, message):
        self.log.configure(state='normal')
        self.log.insert('end', message + '\n')
        self.log.see('end')
        self.log.configure(state='disabled')


        
