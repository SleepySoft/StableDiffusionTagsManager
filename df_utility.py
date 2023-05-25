import random
import string
import traceback

import requests
import pandas as pd
from pandas._testing import assert_frame_equal

RIGHT_INDICATOR = "__Right_Sleepy_299792458"


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


def translate_df(df, text_field, trans_field, use_cache: bool, offline: bool = False) -> bool:
    """
    Translates the text in the specified text_field of each row of the dataframe using youdao_translate function
    and fills the result to the specified trans_field if the trans_field is empty string.
    Optimised by new bing.

    Args:
        df (pandas.DataFrame): The dataframe to translate.
        text_field (str): The name of the field containing the text to translate.
        trans_field (str): The name of the field to fill with the translation.
        use_cache (bool): If True. Use cache else always do translation.
        offline (bool): If True. Only use cache for translation

    Returns:
        None
    """

    def translate_text(row) -> str:
        if not row[trans_field]:
            original_text = row[text_field]
            translated_text = None
            if use_cache and original_text in translate_cache.keys():
                translated_text = translate_cache[original_text]
            if translated_text is None and not offline:
                translated_text = youdao_translate(original_text)
                translate_cache[original_text] = translated_text
            return '' if translated_text is None else translated_text
        return row[trans_field]

    if not df.empty:
        try:
            df[trans_field] = df.apply(translate_text, axis=1)
            return True
        except Exception as e:
            print(e)
            return False
        finally:
            pass
    else:
        return True


def merge_df_keeping_left_value(left: pd.DataFrame, right: pd.DataFrame, on: str):
    df = left.merge(right, on=on, how='left', suffixes=('', '_y'))
    df = df.drop([col for col in df.columns if col.endswith('_y')], axis=1)
    df = df.fillna('')
    return df


def update_df_from_right_value(df_left: pd.DataFrame, df_right: pd.DataFrame,
                               primary_key: str, update_fields: list or None = None) -> pd.DataFrame:
    assert primary_key in df_left.columns, f"{primary_key} not in df_left columns"
    assert primary_key in df_right.columns, f"{primary_key} not in df_right columns"

    df_merged = pd.merge(df_left, df_right, on=primary_key, how='left', suffixes=('', RIGHT_INDICATOR))
    for col in df_merged.columns:
        if col.endswith(RIGHT_INDICATOR):
            left_col = col[:-len(RIGHT_INDICATOR)]
            if (update_fields is None) or (left_col in update_fields):
                df_merged[left_col] = df_merged[col].where(df_merged[col].notnull(), df_merged[left_col])
            df_merged.drop(col, axis=1, inplace=True)

    df_merged.fillna('', inplace=True)
    return df_merged


def update_df_from_right_value_if_empty(df_left: pd.DataFrame, df_right: pd.DataFrame,
                                        primary_key: str, update_fields: list or None = None) -> pd.DataFrame:
    assert primary_key in df_left.columns, f"{primary_key} not in df_left columns"
    assert primary_key in df_right.columns, f"{primary_key} not in df_right columns"

    df_merged = pd.merge(df_left, df_right, on=primary_key, how='left', suffixes=('', RIGHT_INDICATOR))
    for col in df_merged.columns:
        if col.endswith(RIGHT_INDICATOR):
            left_col = col[:-len(RIGHT_INDICATOR)]
            if (update_fields is None) or (left_col in update_fields):
                df_merged[left_col].mask(
                    df_merged[left_col].isnull() | (df_merged[left_col] == '') | df_merged[left_col].isna(),
                    df_merged[col], inplace=True)
            df_merged.drop(col, axis=1, inplace=True)

    df_merged.fillna('', inplace=True)
    return df_merged


def upsert_df_from_right(df_left: pd.DataFrame, df_right: pd.DataFrame, primary_key: str) -> pd.DataFrame:
    assert primary_key in df_left.columns, f"{primary_key} not in df_left columns"
    assert primary_key in df_right.columns, f"{primary_key} not in df_right columns"

    df_merged = pd.merge(df_left, df_right, on=primary_key, how='outer', suffixes=('', RIGHT_INDICATOR), indicator=True)
    for col in df_merged.columns:
        if col.endswith(RIGHT_INDICATOR):
            left_col = col[:-len(RIGHT_INDICATOR)]
            df_merged[left_col] = df_merged[left_col].mask(
                (df_merged['_merge'] == 'both') | (df_merged['_merge'] == 'right_only'), df_merged[col])
            df_merged.drop(col, axis=1, inplace=True)

    df_merged.drop('_merge', axis=1, inplace=True)
    df_merged.fillna('', inplace=True)
    return df_merged


# def update_df_by_dicts(df: pd.DataFrame, data: dict or [dict], primary_key: str):
#     if primary_key not in df.columns:
#         raise ValueError(f"Primary key '{primary_key}' not found in DataFrame columns")
#
#     if isinstance(data, dict):
#         data = [data]
#
#     for d in data:
#         if primary_key not in d.keys():
#             raise ValueError(f"Primary key '{primary_key}' not found in data key")
#
#         mask = df[primary_key] == row[primary_key]
#         for key in row:
#             if key in df.columns:
#                 df.loc[mask, key] = row[key]


def concat_df_exclude(df1: pd.DataFrame, df2: pd.DataFrame, df3: pd.DataFrame, primary_key: str):
    """
    Concatenates two DataFrames and excludes rows from the first DataFrame based on a third DataFrame and a primary key.

    Args:
        df1 (DataFrame): The first DataFrame.
        df2 (DataFrame): The second DataFrame. If not None, columns that exist in df2 but not in df1 are added to df1.
        df3 (DataFrame): The third DataFrame. If not None, rows that exist in df3 are removed from df1.
        primary_key (str): The name of the primary key column. Subsequent operations are based on this column.

    Returns:
        DataFrame: The modified first DataFrame.
    """
    if df2 is not None:
        df1 = df1.drop_duplicates(subset=primary_key)
        df2 = df2.drop_duplicates(subset=primary_key)
        df2 = df2[~df2[primary_key].isin(df1[primary_key])]
        df1 = pd.concat([df1, df2], axis=0)
    if df3 is not None:
        df1 = df1[~df1[primary_key].isin(df3[primary_key])]
    return df1


# ----------------------------------------------------------------------------------------------------------------------
# Test case are generated by new Bing and adjust by manual
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


def check_update_df_from_right_value():
    df_left = create_df_left()
    df_right = create_df_right()
    df_new = update_df_from_right_value(df_left, df_right, 'tag')
    print(df_new)


def test_merge_df_keeping_left_value():
    """
    left             right              result
       A  B         A    B  C           A  B  C
    0  1  3      0  1  100  5        0  1  5  5
    1  2  4      1  3  200  6        1  3  6  ''
    :return:
    """
    df_left = pd.DataFrame({'A': [1, 2], 'B': [3, 4]})
    df_right = pd.DataFrame({'A': [1, 3], 'B': [100, 200], 'C': [5, 6]})

    result = merge_df_keeping_left_value(df_left, df_right, on='A')

    expected_result = pd.DataFrame({'A': [1, 2], 'B': [3, 4], 'C': [5, '']})
    pd.testing.assert_frame_equal(result, expected_result)


def test_update_df_from_right_value_1():
    """
      left         right             result
       A  B         A  B  C           A  B  C
    0  1  3      0  1  5  7        0  1  5  7
    1  2  4      1  3  6  8        1  2  4  ''
    :return:
    """

    df_left = pd.DataFrame({'A': [1, 2], 'B': [3, 4]})
    df_right = pd.DataFrame({'A': [1, 3], 'B': [5, 6], 'C': [7, 8]})

    result = update_df_from_right_value(df_left, df_right, 'A')
    expected_result = pd.DataFrame({'A': [1, 2], 'B': [5.0, 4.0], 'C': [7.0, '']})
    pd.testing.assert_frame_equal(result, expected_result)


def test_update_df_from_right_value_2():
    """
    left           right              result
       A  B         A  C           A  B  C
    0  1  3      0  1  5        0  1  3  5
    1  2  4      1  3  6        1  2  4  ''
    :return:
    """

    df_left = pd.DataFrame({'A': [1, 2], 'B': [3, 4]})
    df_right = pd.DataFrame({'A': [1, 3], 'C': [5, 6]})

    result = update_df_from_right_value(df_left, df_right, 'A')
    expected_result = pd.DataFrame({'A': [1, 2], 'B': [3, 4], 'C': [5.0, '']})
    pd.testing.assert_frame_equal(result, expected_result)


def test_update_df_from_right_value_3():
    """
    left         right          result
       A          A  B           A  B
    0  1       0  1  5        0  1  5
    1  2       1  3  6        1  2  ’‘
    :return:
    """

    df_left = pd.DataFrame({'A': [1, 2]})
    df_right = pd.DataFrame({'A': [1, 3], 'B': [5, 6]})

    result = update_df_from_right_value(df_left, df_right, 'A')
    expected_result = pd.DataFrame({'A': [1, 2], 'B': [5.0, '']})
    pd.testing.assert_frame_equal(result, expected_result)


def test_update_df_from_right_value_if_empty_1():
    """
       left           right          result
       A  B           A  B  C         A  B  C
    0  1  3        0  1  5  7      0  1  3  7
    1  2  None     1  2  6  8      1  2  6  8
    :return:
    """

    df_left = pd.DataFrame({'A': [1, 2], 'B': [3, None]})
    df_right = pd.DataFrame({'A': [1, 2], 'B': [5, 6], 'C': [7, 8]})

    result = update_df_from_right_value_if_empty(df_left, df_right, 'A')
    expected_result = pd.DataFrame({'A': [1, 2], 'B': [3.0, 6.0], 'C': [7, 8]})
    pd.testing.assert_frame_equal(result, expected_result)


def test_update_df_from_right_value_if_empty_2():
    """
       left           right          result
       A  B           A  B  C         A  B  C
    0  1  ''       0  1  5  7      0  1  5  7
    1  2  4        1  3  6  8      1  2  4  8

    :return:
    """

    df_left = pd.DataFrame({'A': [1, 2], 'B': ['', 4]})
    df_right = pd.DataFrame({'A': [1, 3], 'B': [5, 6], 'C': [7, '']})

    result = update_df_from_right_value_if_empty(df_left, df_right, 'A')
    expected_result = pd.DataFrame({'A': [1, 2], 'B': [5.0, 4.0], 'C': [7, '']})
    pd.testing.assert_frame_equal(result, expected_result)


def test_update_df_from_right_value_if_empty_3():
    """
     left      right          result
       A        A  B         A  B
    0  1     0  1  5      0  1  5
    1  2     1  3  6      1  2  ''

    :return:
    """

    df_left = pd.DataFrame({'A': [1, 2]})
    df_right = pd.DataFrame({'A': [1, 3], 'B': [5, 6]})

    result = update_df_from_right_value_if_empty(df_left, df_right, 'A')
    expected_result = pd.DataFrame({'A': [1, 2], 'B': [5.0, '']})
    pd.testing.assert_frame_equal(result, expected_result)


def test_upsert_df_from_right():
    """
               left                       right                     result
       id  value extra_left       id  value  extra_right        id  value extra_left extra_right
    0  1     a      x          0  2     x        p           0  1     a       x          ''
    1  2     b      y          1  3     y        q           1  2     x       y          p
    2  3     c      z          2  4     z        r           2  3     y       z          q
                               3  5     w        s           3  4     z       ''         r
                                                             4  5     w       ''         s
    :return:
    """

    data_left = {'id': [1, 2, 3], 'value': ['a', 'b', 'c'], 'extra_left': ['x', 'y', 'z']}
    df_left = pd.DataFrame(data_left)

    data_right = {'id': [2, 3, 4, 5], 'value': ['x', 'y', 'z', 'w'], 'extra_right': ['p', 'q', 'r', 's']}
    df_right = pd.DataFrame(data_right)

    df_merged = upsert_df_from_right(df_left, df_right, 'id')

    expected_data = {'id': [1, 2, 3, 4, 5],
                     'value': ['a', 'x', 'y', 'z', 'w'],
                     'extra_left': ['x', 'y', 'z', '', ''],
                     'extra_right': ['', 'p', 'q', 'r', 's']}
    expected_df = pd.DataFrame(expected_data)

    pd.testing.assert_frame_equal(df_merged, expected_df)


# def test_update_df_by_dicts_1():
#     # Test case 1: data is a dict and data's keys exist in df
#     df = pd.DataFrame({'A': [1, 2], 'B': [3, 4]})
#     data = {'A': 1, 'B': 6}
#     primary_key = 'A'
#     expected_df = pd.DataFrame({'A': [1, 2], 'B': [6, 4]})
#
#     update_df_by_dicts(df, data, primary_key)
#     assert_frame_equal(df, expected_df)
#
#
# def test_update_df_by_dicts_2():
#     # Test case 2: data is a dict and data's keys do not exist in df
#     df = pd.DataFrame({'A': [1, 2], 'B': [3, 4]})
#     data = {'A': 1, 'C': 5}
#     primary_key = 'A'
#     expected_df = pd.DataFrame({'A': [1, 2], 'B': [3, 4]})
#
#     update_df_by_dicts(df, data, primary_key)
#     assert_frame_equal(df, expected_df)
#
#
# def test_update_df_by_dicts_3():
#     # Test case 3: data is a list of dicts and can update multiple rows
#     df = pd.DataFrame({'A': [1, 2], 'B': [3, 4]})
#     data = [{'A': 1, 'B': 6}, {'A': 2, 'B': 8}]
#     primary_key = 'A'
#     expected_df = pd.DataFrame({'A': [1, 2], 'B': [6, 8]})
#
#     update_df_by_dicts(df, data, primary_key)
#     assert_frame_equal(df, expected_df)
#
#
# def test_update_df_by_dicts_4():
#     # Test case 4: data is a list of dicts and cannot update any rows
#     df = pd.DataFrame({'A': [1, 2], 'B': [3, 4]})
#     data = [{'A': 5, 'B': 6}, {'A': 7, 'B': 8}]
#     primary_key = 'A'
#     expected_df = pd.DataFrame({'A': [1, 2], 'B': [3, 4]})
#
#     update_df_by_dicts(df, data, primary_key)
#     assert_frame_equal(df, expected_df)
#
#
# def test_update_df_by_dicts_5():
#     # Test case 5: data is a list of dicts and can partially update rows
#     df = pd.DataFrame({'A': [1, 2], 'B': [3, 4]})
#     data = [{'A': 1, 'B': 6}, {'A': 7, 'B': 8}]
#     primary_key = 'A'
#     expected_df = pd.DataFrame({'A': [1, 2], 'B': [6, 4]})
#
#     update_df_by_dicts(df, data, primary_key)
#     assert_frame_equal(df, expected_df)
#
#
# def test_update_df_by_dicts_6():
#     # Test case 6: primary_key is not in df's columns
#     df = pd.DataFrame({'A': [1, 2], 'B': [3, 4]})
#     data = [{'A': 1, 'B': 6}, {'A': 7, 'B': 8}]
#     primary_key = 'C'
#
#     try:
#         update_df_by_dicts(df, data, primary_key)
#     except ValueError as e:
#         assert str(e) == f"Primary key '{primary_key}' not found in DataFrame columns"


# ----------------------------------------------------------------------------------------------------------------------

# Why the expect df includes float type. From new Bing:
# 这是因为在合并两个DataFrame时，pandas会自动将整数列转换为浮点型，以便能够表示缺失值（NaN）。
# 在这种情况下，由于 df_right 中没有与 df_left 中的第二行匹配的行（即 A 列中没有值为2的行），
# 因此合并后的DataFrame中第二行的 C 列将包含缺失值。
# 由于缺失值不能用整数表示，所以pandas将列 C 的数据类型更改为了浮点型。

def main():
    test_merge_df_keeping_left_value()

    test_update_df_from_right_value_1()
    test_update_df_from_right_value_2()
    test_update_df_from_right_value_3()

    test_update_df_from_right_value_if_empty_1()
    test_update_df_from_right_value_if_empty_2()
    test_update_df_from_right_value_if_empty_3()

    test_upsert_df_from_right()

    # test_update_df_by_dicts_1()
    # test_update_df_by_dicts_2()
    # test_update_df_by_dicts_3()
    # test_update_df_by_dicts_4()
    # test_update_df_by_dicts_5()
    # test_update_df_by_dicts_6()


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print('Error =>', e)
        print('Error =>', traceback.format_exc())
        exit()
    finally:
        pass
