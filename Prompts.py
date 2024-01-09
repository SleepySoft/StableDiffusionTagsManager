import re
from itertools import chain
from typing import Tuple, Union

from TagManager import DATABASE_FIELDS, PRIMARY_KEY
from app_utility import *

SPECIAL_KEYWORDS = ['BREAK']

WEIGHT_INC_BASE = 1.1
WEIGHT_DEC_BASE = 0.9


EXTRA_FLAGS = ['ENSD:', 'Seed:', 'Model:']


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


def is_kv_like(prompt_line: str):
    # 按逗号分割字符串
    items = prompt_line.split(',')
    for item in items:
        if item.strip() == '':
            continue
        # 检查每一项是否由冒号分隔key和value
        if ':' not in item:
            return False
        key, _ = item.split(':')
        if len(key.strip()) == 0:
            return False
    return True


def guess_prompt_group(prompt_line: str) -> Tuple[str, Union[str, dict]]:
    if prompt_line.strip() == '':
        return '', prompt_line

    match = re.match(r"^\s*positive prompt[:：]?\s*(.*)$", prompt_line, re.I)
    if match:
        return 'positive', match.group(1)

    match = re.match(r"^\s*negative prompt[:：]?\s*(.*)$", prompt_line, re.I)
    if match:
        return 'negative', match.group(1)

    if all(flag in prompt_line for flag in EXTRA_FLAGS) and is_kv_like(prompt_line):
        return 'extra', prompt_line

    return '', prompt_line


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
            with open(file_name, 'rt', encoding='utf-8') as f:
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
        positive_tags = list(chain.from_iterable(Prompts.split_prompt(line) for line in positive_lines))
        negative_tags = list(chain.from_iterable(Prompts.split_prompt(line) for line in negative_lines))
        return positive_tags, negative_tags, '\n'.join(extra_data_lines)

    @staticmethod
    def group_prompts(prompt_text: str):
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
                    prompt_flag = 'negative'
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

    @staticmethod
    def split_prompt(prompt_line: str):
        # 匹配被括号包围的内容
        bracket_patterns = [r'\([^()]*\)', r'\[[^[]*\]', r'\{[^{}]*\}', r'<[^<>]*>']
        bracket_contents = []
        for pattern in bracket_patterns:
            while re.search(pattern, prompt_line):
                match = re.search(pattern, prompt_line)
                bracket_contents.append(match.group())
                prompt_line = prompt_line[:match.start()] + prompt_line[match.end():]

        # 按逗号分割
        comma_contents = re.split(r'[，,]', prompt_line)
        # 去除空白内容
        comma_contents = [content.strip() for content in comma_contents if content.strip()]

        return bracket_contents + comma_contents

    @staticmethod
    def parse_addition_network(raw_tag: str):
        # 去掉首尾的"<>"
        raw_tag = raw_tag.strip('<>')
        # 以":"分割字符串
        tag_parts = raw_tag.split(':')

        try:
            # 尝试返回tag_parts[0] + ":" + tag_parts[1], float(tag_parts[2])
            return tag_parts[0] + ":" + tag_parts[1], float(tag_parts[2])
        except (IndexError, ValueError):
            try:
                # 如果出错，尝试返回tag_parts[0] + ":"
                return tag_parts[0] + ":" + tag_parts[1], 0
            except IndexError:
                # 如果还出错，返回tag_parts[0] + ":?"
                return tag_parts[0] + ":?", 0

    @staticmethod
    def tags_list_to_tag_data(tags: [str]) -> dict:
        data_tag = []
        data_weight = []
        for tag in tags:
            raw_tags, tag_weights = Prompts.analysis_raw_tag(tag)
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
    def analysis_raw_tag(raw_tag):
        tags = []
        weights = []
        if raw_tag.startswith('<') and raw_tag.endswith('>'):
            t, w = Prompts.parse_addition_network(raw_tag)
            tags.append(t)
            weights.append(w)
        elif raw_tag.startswith('{') and raw_tag.endswith('}'):
            if '|' in raw_tag or ',' in raw_tag:
                parts = re.split('[|,]', raw_tag[1:-1])
                for part in parts:
                    t, w = Prompts.analysis_raw_tag(part)
                    tags.extend(t)
                    weights.extend(w)
            else:
                tag, weight = parse_wrapper(raw_tag, '{', '}', WEIGHT_INC_BASE)
                tags.append(tag)
                weights.append(weight)
        elif raw_tag.startswith('[') and raw_tag.endswith(']'):
            tag, weight = parse_wrapper(raw_tag, '[', ']', WEIGHT_DEC_BASE)
            tags.append(tag)
            weights.append(weight)
        elif raw_tag.startswith('(') and raw_tag.endswith(')'):
            parts = raw_tag[1:-1].split(',')
            for part in parts:
                t, w = Prompts.analysis_raw_tag(part)
                tags.extend(t)
                weights.extend(w)
        else:
            parts = raw_tag.split(':')
            tags.append(parts[0])
            weights.append(try_float(parts[1], 1.0) if len(parts) > 1 else 1.0)
        return tags, weights

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
