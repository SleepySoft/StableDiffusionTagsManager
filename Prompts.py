import re
from typing import Tuple, Union

from TagManager import DATABASE_FIELDS, PRIMARY_KEY
from app_utility import *

SPECIAL_KEYWORDS = ['BREAK']

WEIGHT_INC_BASE = 1.1
WEIGHT_DEC_BASE = 0.9


def try_float(text: str, on_fail: float or None = None) -> float or None:
    try:
        return float(text)
    except ValueError:
        return on_fail
    finally:
        pass


def parse_wrapper(tag: str, left: str, right: str, base: float) -> (str, float):
    tag = tag.strip()
    if tag.startswith(left):  # and tag.endswith(right):
        n = tag.count(left)
        weight = base ** n
    else:
        weight = 1.0
    return tag.replace(left, '').replace(right, ''), weight


def parse_tag_colon_weight(tag: str) -> (str, float):
    if ':' in tag:
        parts = tag.split(':')
        weight = try_float(parts[1])
        return parts[0], (weight if weight else 1.0)
    else:
        return tag, 1.0


def guess_prompt_group(prompt_line: str) -> Tuple[str, Union[str, dict]]:
    if prompt_line.strip() == '':
        return '', prompt_line

    match = re.match(r"^\s*positive prompt[:：]?\s*(.*)$", prompt_line, re.I)
    if match:
        return 'positive', match.group(1)

    match = re.match(r"^\s*negative prompt[:：]?\s*(.*)$", prompt_line, re.I)
    if match:
        return 'negative', match.group(1)

    # 按逗号分割字符串
    items = prompt_line.split(',')

    for item in items:
        if item.strip() == '':
            continue

        # 检查每一项是否由冒号分隔key和value
        if not ':' in item:
            return '', prompt_line

        key, _ = item.split(':')
        if len(key.strip()) == 0:
            return '', prompt_line

    return 'extra', prompt_line


class Prompts:
    def __init__(self):
        self.positive_tag_data_dict = {PRIMARY_KEY: [], 'weight': []}
        self.negative_tag_data_dict = {PRIMARY_KEY: [], 'weight': []}
        self.extra_data_string = ''
        self.raw_prompts = ''

    def from_text(self, text: str) -> bool:
        self.raw_prompts = text
        return self.parse_prompt_text(text)

    def from_file(self, file_name: str) -> bool:
        try:
            with open(file_name, 'rt') as f:
                return self.from_text(f.read())
        except Exception as e:
            print(e)
            return False
        finally:
            pass

    def from_record(self, record: [dict], positive: bool) -> bool:
        try:
            tag_data_dict = {
                PRIMARY_KEY: [r[PRIMARY_KEY] for r in record],
                'weight': [r['weight'] for r in record]
            }
            if positive:
                self.positive_tag_data_dict = tag_data_dict
            else:
                self.negative_tag_data_dict = tag_data_dict
            return True
        except Exception as e:
            print(e)
            return False
        finally:
            pass

    def merge(self, other_prompts):
        Prompts.merge_tag_data_dict(self.positive_tag_data_dict, other_prompts.positive_tag_data_dict)
        Prompts.merge_tag_data_dict(self.negative_tag_data_dict, other_prompts.negative_tag_data_dict)
        # self.extra_data_string += other_prompts.extra_data_string

    def parse_prompt_text(self, text: str):
        positive_tags, negative_tags, self.extra_data_string = Prompts.parse_prompts(text)
        self.positive_tag_data_dict = Prompts.tags_list_to_tag_data(unique_list(positive_tags))
        self.negative_tag_data_dict = Prompts.tags_list_to_tag_data(unique_list(negative_tags))
        return True

    def positive_tag_string(self, includes_weight: bool) -> str:
        return Prompts.tag_data_dict_to_string(self.positive_tag_data_dict, includes_weight)

    def negative_tag_string(self, includes_weight: bool) -> str:
        return Prompts.tag_data_dict_to_string(self.negative_tag_data_dict, includes_weight)

    def re_format_extra_string(self) -> str:
        extra_data = self.parse_extra_info(self.extra_data_string)
        return '\n'.join([f"{key}: {value}" for key, value in extra_data.items()])

    @staticmethod
    def tag_data_dict_to_string(tag_data_dict: dict, includes_weight: bool) -> str:
        tags_with_weight = [('(%s:%s)' % (t, round(try_float(w, 1.0), 2))
                             if includes_weight and (w != '') and (try_float(w, 1.0) - 1 > 0.001) else t)
                            for t, w in zip(tag_data_dict[PRIMARY_KEY],
                                            tag_data_dict['weight'])]
        return ', '.join(tags_with_weight)

    @staticmethod
    def parse_extra_info(text: str) -> dict:
        extra_info = {}
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue
            items = line.split(',')
            for item in items:
                if ':' not in item:
                    continue
                key, value = item.split(':', 1)
                key = key.strip()
                value = value.strip()
                extra_info[key] = value
        return extra_info

    @staticmethod
    def parse_prompts(prompt_text: str):
        positive_lines, negative_lines, extra_data_lines = Prompts.group_prompts(prompt_text)

    def group_prompts(self, prompt_text: str):
        lines = prompt_text.split('\n')
        lines = [line.strip() for line in lines]

        empty_line_count = 0
        prompt_flag = 'positive'

        positive_lines = []
        negative_lines = []
        extra_data_lines = []

        for line in lines:
            group, sanitized_line = guess_prompt_group(line)

            if sanitized_line == '':
                empty_line_count += 1
            else:
                empty_line_count = 0

            if group == 'extra':
                prompt_flag = 'extra'

            if prompt_flag == 'positive':
                if group == 'positive':
                    positive_lines.clear()
                if group == 'negative':
                    prompt_flag = 'positive'
                if empty_line_count > 0:
                    prompt_flag = 'maybe_negative'

            elif prompt_flag == 'maybe_negative':
                if group == 'negative' or empty_line_count > 1:
                    positive_lines += negative_lines
                    negative_lines.clear()
                    prompt_flag = 'negative'

            elif prompt_flag == 'negative':
                pass
            elif prompt_flag == 'extra':
                pass
            else:
                assert False

            {
                'positive': positive_lines,
                'maybe_negative': negative_lines,
                'negative': negative_lines,
                'extra': extra_data_lines
            }[prompt_flag].append(sanitized_line)

        return positive_lines, negative_lines, extra_data_lines

    # @staticmethod
    # def parse_prompts(prompt_text: str):
    #     lines = prompt_text.split('\n')
    #     lines = [line.strip() for line in lines]
    #     prompt_text = '\n'.join(lines)
    #
    #     positive_start = prompt_text.lower().find('positive prompt')
    #     if positive_start != -1:
    #         positive_start += len('positive prompt')
    #         positive_start = prompt_text.find(':', positive_start) + 1
    #     else:
    #         positive_start = 0
    #
    #     negative_start = prompt_text.lower().find('negative prompt')
    #     if negative_start != -1:
    #         positive_end = negative_start
    #         negative_start += len('negative prompt')
    #         negative_start = prompt_text.find(':', negative_start) + 1
    #         negative_end = prompt_text.find('\n', negative_start)
    #     else:
    #         # Find the position of two consecutive newlines
    #         double_newline_pos = prompt_text.find('\n\n')
    #         if double_newline_pos != -1:
    #             positive_end = double_newline_pos
    #         else:
    #             first_line_end = prompt_text.find('\n')
    #             second_line_end = prompt_text.find('\n', first_line_end + 1)
    #             positive_end = first_line_end if first_line_end > 0 else len(prompt_text)
    #
    #         negative_start = positive_end
    #         negative_end = second_line_end if second_line_end > 0 else len(prompt_text)
    #
    #     positive_tags_string = prompt_text[positive_start:positive_end].strip()
    #     negative_tags_string = prompt_text[negative_start:negative_end].strip()
    #     for keyword in SPECIAL_KEYWORDS:
    #         positive_tags_string = positive_tags_string.replace(keyword, ',')
    #         negative_tags_string = negative_tags_string.replace(keyword, ',')
    #     extra_data_string = prompt_text[negative_end + 1:].strip() if negative_end > 0 else ''
    #
    #     positive_tags_raw = positive_tags_string.replace('\n', ',').split(',')
    #     negative_tags_raw = negative_tags_string.replace('\n', ',').split(',')
    #
    #     positive_tags = [tag.strip() for tag in positive_tags_raw if tag.strip() != '']
    #     negative_tags = [tag.strip() for tag in negative_tags_raw if tag.strip() != '']
    #
    #     return positive_tags, negative_tags, extra_data_string

    @staticmethod
    def tags_list_to_tag_data(tags: [str]) -> dict:
        data_tag = []
        data_weight = []
        for tag in tags:
            raw_tags, tag_weights = Prompts.analysis_tag(tag)
            if len(raw_tags) == 0:
                continue
            for raw_tag, tag_weight in zip(raw_tags, tag_weights):
                raw_tag = raw_tag.strip()
                if raw_tag == '':
                    continue
                # Process the duplicate case
                if raw_tag not in data_tag:
                    data_tag.append(raw_tag)
                    data_weight.append(format_float(tag_weight))
                else:
                    index = data_tag.index(raw_tag)
                    data_weight[index] = format_float(float(data_weight[index]) * float(tag_weight))
        return {
            PRIMARY_KEY: data_tag,
            'weight': data_weight
        }

    @staticmethod
    def analysis_tag(tag: str):
        weight_list = []
        tag_list = []
        if tag.startswith('[') or tag.endswith(']'):
            raw_tag, weight = parse_wrapper(tag, '[', ']', WEIGHT_DEC_BASE)
            pure_tag, weight2 = parse_tag_colon_weight(raw_tag)
            tag_list.append(pure_tag)
            weight_list.append(weight * weight2)
        elif tag.startswith('{') or tag.endswith('}'):
            raw_tag, weight = parse_wrapper(tag, '{', '}', WEIGHT_INC_BASE)
            pure_tag, weight2 = parse_tag_colon_weight(raw_tag)
            tag_list.append(pure_tag)
            weight_list.append(weight * weight2)
        elif tag.startswith('(') or tag.endswith(')'):
            # TODO: Cannot parse (A, B, C: weight)
            if ':' in tag:
                sub_tags = tag.replace('(', '').replace(')', '').split(':')
                for sub_tag in sub_tags:
                    weight = try_float(sub_tag)
                    if weight:
                        weight_list.append(weight)
                    else:
                        tag_list.append(sub_tag)
            else:
                raw_tag, weight = parse_wrapper(tag, '(', ')', WEIGHT_INC_BASE)
                pure_tag, weight2 = parse_tag_colon_weight(raw_tag)
                tag_list.append(pure_tag)
                weight_list.append(weight * weight2)
        elif tag.startswith('<'):
            sub_tags = tag.replace('<', '').replace('>', '').split(':')

            weight = try_float(sub_tags[2]) if len(sub_tags) > 2 else None
            weight = 1.0 if weight is None else weight
            raw_tag = sub_tags[0] + ':' + sub_tags[1] if len(sub_tags) > 1 else sub_tags[0]

            tag_list.append(raw_tag)
            weight_list.append(weight)
        else:
            tag, weight = parse_tag_colon_weight(tag)
            tag_list.append(tag)
            weight_list.append(weight)

        return tag_list, weight_list

    @staticmethod
    def merge_tag_data_dict(base: dict, update: dict):
        for tag, weight in zip(update[PRIMARY_KEY], update['weight']):
            try:
                if tag in base[PRIMARY_KEY]:
                    index = base[PRIMARY_KEY].index(tag)
                    adjust_weight = try_float(base['weight'][index], 1.0) + 0.1  # + try_float(weight, 1.0)- 1.0
                    base['weight'][index] = max(adjust_weight, 0.1)
                else:
                    base[PRIMARY_KEY].append(tag)
                    base['weight'].append(weight)
            except Exception as e:
                print(e)
            finally:
                pass


def test_parse_tag():
    print(Prompts.analysis_tag("<lora:add_detail:1.5>"))
    print(Prompts.analysis_tag("<lora:add_detail>"))
    print(Prompts.analysis_tag("<lora"))

    print(Prompts.analysis_tag("tag"))
    print(Prompts.analysis_tag("(tag:1.2)"))
    print(Prompts.analysis_tag("(tag1:tag2:1.1:1.2)"))

    print(Prompts.analysis_tag("(abc)"))
    print(Prompts.analysis_tag("((abc))"))
    print(Prompts.analysis_tag("(((abc)))"))

    print(Prompts.analysis_tag("{def}"))
    print(Prompts.analysis_tag("{{def}}"))
    print(Prompts.analysis_tag("{{{def}}}"))

    print(Prompts.analysis_tag("[xyz]"))
    print(Prompts.analysis_tag("[[xyz]]"))
    print(Prompts.analysis_tag("[[[xyz]]]"))
