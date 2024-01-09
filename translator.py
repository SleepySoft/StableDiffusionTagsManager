import threading

ts = None
timeout = 3


class ImportThread(threading.Thread):
    def __init__(self):
        super(ImportThread, self).__init__()

    def run(self):
        try:
            import translators
            global ts
            ts = translators
        except Exception as e:
            print(e)
        finally:
            pass


def translator_available() -> bool:
    return ts is not None


thread = ImportThread()
thread.start()

# thread.join(timeout)
#
# if thread.is_alive():
#     print(f"Import translator module fail, timeout = {timeout}s. The translate feature maybe not available.")


translate_cache = {}

translator_list = ['alibaba', 'baidu', 'youdao', 'google', 'bing', 'niutrans', 'mymemory', 'modernmt', 'volcengine',
                   'iciba', 'iflytek', 'lingvanex', 'yandex', 'itranslate', 'systran', 'argos', 'apertium', 'reverso',
                   'deepl', 'cloudtranslation', 'qqtransmart', 'translatecom', 'sogou', 'tilde', 'qqfanyi', 'papago',
                   'translateme', 'mirai', 'iflyrec', 'yeekit', 'languagewire', 'caiyun', 'elia', 'judic', 'mglip',
                   'utibet']


def translate(original_text: str, translator: str, use_cache: bool = True, offline: bool = False):
    translated_text = translate_cache[original_text] \
        if use_cache and original_text in translate_cache.keys() else None
    if translated_text is None and not offline and ts is not None:
        translated_text = ts.translate_text(
            query_text=original_text,
            translator=translator,
            from_language='en',
            to_language='cn',
            timeout=1)
        translate_cache[original_text] = translated_text
    return '' if translated_text is None else translated_text
