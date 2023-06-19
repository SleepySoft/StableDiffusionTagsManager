python -m venv pack
call pack\Scripts\activate
pip install -r requirements.txt
pyinstaller.exe -w -i doc/s.ico --add-data "public.csv;." --add-data "depot;depot" --add-data "README.md;." main.py
