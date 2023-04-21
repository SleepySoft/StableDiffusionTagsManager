python -m venv pack
call pack\Scripts\activate
pip install -r Requirements.txt
pyinstaller.exe -w -i doc/s.ico --add-data "public.csv;." main.py
