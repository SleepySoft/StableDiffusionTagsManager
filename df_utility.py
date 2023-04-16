import random
import string
import traceback

import requests
import pandas as pd


# From new Bing
# Thanks youdao providing API KEY free translate service.

def youdao_translate(query, from_lang='AUTO', to_lang='AUTO'):
    url = 'http://fanyi.youdao.com/translate'
    data = {
        "i": query,
        "from": from_lang,
        "to": to_lang,
        "smartresult": "dict",
        "client": "fanyideskweb",
        "salt": "16081210430989",
        "doctype": "json",
        "version": "2.1",
        "keyfrom": "fanyi.web",
        "action": "FY_BY_CLICKBUTTION"
    }
    res = requests.post(url, data=data).json()
    return res['translateResult'][0][0]['tgt']


translate_cache = {}


def translate_df(df, text_field, trans_field, use_cache: bool):
    """
    Translates the text in the specified text_field of each row of the dataframe using youdao_translate function
    and fills the result to the specified trans_field if the trans_field is empty string.
    Optimised by new bing.

    Args:
        df (pandas.DataFrame): The dataframe to translate.
        text_field (str): The name of the field containing the text to translate.
        trans_field (str): The name of the field to fill with the translation.
        use_cache (bool): If yes. Use cache else always do translation.

    Returns:
        None
    """

    def translate_text(row):
        if not row[trans_field]:
            original_text = row[text_field]
            if use_cache:
                if original_text not in translate_cache:
                    translate_cache[original_text] = youdao_translate(original_text)
                translated_text = translate_cache[original_text]
            else:
                translated_text = youdao_translate(original_text)
            return translated_text
        return row[trans_field]

    if not df.empty:
        df[trans_field] = df.apply(translate_text, axis=1)


def merge_df_keeping_left_value(left: pd.DataFrame, right: pd.DataFrame, on: str):
    df = left.merge(right, on=on, how='left', suffixes=('', '_y'))
    df = df.drop([col for col in df.columns if col.endswith('_y')], axis=1)
    df = df.fillna('')
    return df


def update_df_from_right_value(df_left: pd.DataFrame, df_right: pd.DataFrame, primary_key: str) -> pd.DataFrame:
    assert primary_key in df_left.columns, f"{primary_key} not in df_left columns"
    assert primary_key in df_right.columns, f"{primary_key} not in df_right columns"

    df_merged = pd.merge(df_left, df_right, on=primary_key, how='left', suffixes=('', '_right'))
    for col in df_merged.columns:
        if col.endswith('_right'):
            left_col = col[:-6]
            df_merged[left_col] = df_merged[col].where(df_merged[col].notnull(), df_merged[left_col])
            df_merged.drop(col, axis=1, inplace=True)

    df_merged.fillna('', inplace=True)
    return df_merged


def update_df_from_right_value_if_empty(df_left: pd.DataFrame, df_right: pd.DataFrame, primary_key: str) -> pd.DataFrame:
    assert primary_key in df_left.columns, f"{primary_key} not in df_left columns"
    assert primary_key in df_right.columns, f"{primary_key} not in df_right columns"

    df_merged = pd.merge(df_left, df_right, on=primary_key, how='left', suffixes=('', '_right'))
    for col in df_merged.columns:
        if col.endswith('_right'):
            left_col = col[:-6]
            df_merged[left_col] = df_merged[col].where((df_merged[left_col].isnull()) | (df_merged[left_col] == ''),
                                                       df_merged[left_col])
            df_merged.drop(col, axis=1, inplace=True)

    df_merged.fillna('', inplace=True)
    return df_merged


def upsert_df_from_right(df_left: pd.DataFrame, df_right: pd.DataFrame, primary_key: str) -> pd.DataFrame:
    assert primary_key in df_left.columns, f"{primary_key} not in df_left columns"
    assert primary_key in df_right.columns, f"{primary_key} not in df_right columns"

    df_merged = pd.merge(df_left, df_right, on=primary_key, how='outer', suffixes=('', '_right'), indicator=True)
    for col in df_merged.columns:
        if col.endswith('_right'):
            left_col = col[:-6]
            df_merged[left_col] = df_merged[col].where(
                (df_merged['_merge'] == 'both') | (df_merged['_merge'] == 'right_only'), df_merged[left_col])
            df_merged.drop(col, axis=1, inplace=True)

    df_merged.drop('_merge', axis=1, inplace=True)
    return df_merged


# ----------------------------------------------------------------------------------------------------------------------

def create_df_left() -> pd.DataFrame:
    import pandas as pd

    tags = ['A', 'B', 'C', 'D', 'E']
    translates = ['', 'banana', 'cherry', '', 'elephant']

    data = {'tag': tags, 'translate': translates}
    df_left = pd.DataFrame(data)

    return df_left


def create_df_right() -> pd.DataFrame:
    tags = ['D', 'E', 'F', 'G', 'H']
    translates = ['vulture', 'walrus', 'xenops', 'yak', 'zebra']
    col1 = ['dog', 'cat', 'bird', 'fish', 'hamster']
    col2 = ['red', 'orange', 'yellow', 'green', 'blue']
    col3 = ['car', 'bus', 'train', 'plane', 'boat']
    col4 = ['rock', 'pop', 'jazz', 'blues', 'country']
    col5 = ['pizza', 'burger', 'taco', 'sushi', 'pasta']
    col6 = ['soccer', 'basketball', 'tennis', 'golf', 'swimming']

    data = {'tag': tags,
            'translate': translates,
            'col1': col1,
            'col2': col2,
            'col3': col3,
            'col4': col4,
            'col5': col5,
            'col6': col6}
    df_right = pd.DataFrame(data)

    return df_right


def test_update_df_from_right_value():
    df_left = create_df_left()
    df_right = create_df_right()
    df_new = update_df_from_right_value(df_left, df_right, 'tag')
    print(df_new)


# ----------------------------------------------------------------------------------------------------------------------

def main():
    test_update_df_from_right_value()


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print('Error =>', e)
        print('Error =>', traceback.format_exc())
        exit()
    finally:
        pass
