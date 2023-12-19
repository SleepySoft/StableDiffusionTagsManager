import os
import glob
import datetime
import requests
from collections import defaultdict


# Do not use set to keep list order
import shutil


def unique_list(lst: list or tuple) -> list:
    result = []
    [result.append(item) for item in lst if item not in result]
    return result


def format_float(value):
    try:
        value = float(value)
        return f"{value:.2f}"
    except ValueError:
        return str(value)


def backup_file(file_name: str, backup_limit: int):
    # Get the path of the file
    file_path = os.path.abspath(file_name)

    # Get the directory of the file
    file_dir = os.path.dirname(file_path)

    # Create the backup directory if it does not exist
    backup_dir = os.path.join(file_dir, 'backup')
    os.makedirs(backup_dir, exist_ok=True)

    # Get the timestamp
    timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S_%f')[:-3]

    # Get the file extension
    file_ext = os.path.splitext(file_name)[1]

    # Create the backup file name
    backup_file_name = os.path.basename(file_name)
    if file_ext:
        backup_file_name = backup_file_name.replace(file_ext, f'_{timestamp}{file_ext}')
    else:
        backup_file_name = f'{backup_file_name}_{timestamp}'

    # Copy the file to the backup directory
    backup_file_path = os.path.join(backup_dir, backup_file_name)
    shutil.copy2(file_path, backup_file_path)

    # Get the number of backup files
    if file_ext:
        backup_files = glob.glob(
            os.path.join(backup_dir, f'{os.path.basename(file_name).replace(file_ext, "")}_*{file_ext}'))
    else:
        backup_files = glob.glob(os.path.join(backup_dir, f'{os.path.basename(file_name)}_*'))
    num_backup_files = len(backup_files)

    # If the number of backup files is greater than the backup limit, delete the oldest file
    if num_backup_files > backup_limit:
        oldest_file = min(backup_files, key=os.path.getctime)
        os.remove(oldest_file)


def backup_file_safe(file_name: str, backup_limit: int) -> bool:
    try:
        backup_file(file_name, backup_limit)
        return True
    except Exception as e:
        print('Back file error.')
        print(e)
        return False
    finally:
        pass


def convert_list_of_dicts(input_list):
    result = defaultdict(list)
    max_len = 0
    for item in input_list:
        for key, value in item.items():
            result[key].append(value)
            max_len = max(max_len, len(result[key]))
    for key in result:
        result[key] += [None] * (max_len - len(result[key]))
    return result


def set_global_proxy(proxy_dict):
    """
    为全局的requests设置代理。

    参数:
    proxy_dict (dict): 代理字典，格式为{'http': 'http://10.10.1.10:3128', 'https': 'https://10.10.1.10:1080'}。
    """
    session = requests.Session()
    session.proxies.update(proxy_dict)
    requests.adapters.DEFAULT_RETRIES = 5
    requests.session().keep_alive = False
    requests.adapters.HTTPAdapter(pool_connections=100, pool_maxsize=100)
    requests.Session().mount('http://', requests.adapters.HTTPAdapter(max_retries=3))
    requests.Session().mount('https://', requests.adapters.HTTPAdapter(max_retries=3))
    requests.sessions.default = session

