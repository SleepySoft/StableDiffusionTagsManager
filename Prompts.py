import pandas as pd

from TagManager import DATABASE_FIELDS, PRIMARY_KEY
from app_utility import *


def try_float(text: str) -> float or None:
    try:
        return float(text)
    except ValueError:
        return None
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


class Prompts:
    def __init__(self):
        self.positive_tag_data_dict = {PRIMARY_KEY: [], 'weight': []}
        self.negative_tag_data_dict = {PRIMARY_KEY: [], 'weight': []}
        self.extra_data_string = ''

    def from_text(self, text: str) -> bool:
        return self.parse_prompt_text(text)

    def from_file(self, file_name: str) -> bool:
        with open(file_name, 'rt') as f:
            return self.from_text(f.read())

    def parse_prompt_text(self, text: str):
        positive_tags, negative_tags, self.extra_data_string = Prompts.parse_prompts(text)
        self.positive_tag_data_dict = Prompts.tags_list_to_tag_data(unique_list(positive_tags))
        self.negative_tag_data_dict = Prompts.tags_list_to_tag_data(unique_list(negative_tags))
        return True

    def positive_tag_string(self) -> str:
        return Prompts.tag_data_dict_to_string(self.positive_tag_data_dict)

    def negative_tag_string(self) -> str:
        return Prompts.tag_data_dict_to_string(self.negative_tag_data_dict)

    def re_format_extra_string(self) -> str:
        extra_data = self.parse_extra_info(self.extra_data_string)
        return '\n'.join([f"{key}: {value}" for key, value in extra_data.items()])

    @staticmethod
    def tag_data_dict_to_string(tag_data_dict: dict) -> str:
        tags_with_weight = [('(%s:%s)' % (t, w) if w != '' else t)
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
        prompt_text = prompt_text.strip()
        lines = prompt_text.split('\n')
        lines = [line for line in lines if line.strip() != '']
        prompt_text = '\n'.join(lines)

        positive_start = prompt_text.lower().find('positive prompt')
        if positive_start != -1:
            positive_start = prompt_text.find(':', positive_start) + 1
        else:
            positive_start = 0

        negative_start = prompt_text.lower().find('negative prompt')
        if negative_start != -1:
            positive_end = negative_start
            negative_start = prompt_text.find(':', negative_start) + 1
            negative_end = prompt_text.find('\n', negative_start)
        else:
            first_line_end = prompt_text.find('\n')
            positive_end = first_line_end if first_line_end > 0 else len(prompt_text)
            negative_start = positive_end
            negative_end = positive_end

        positive_tags_string = prompt_text[positive_start:positive_end].strip()
        negative_tags_string = prompt_text[negative_start:negative_end].strip()
        extra_data_string = prompt_text[negative_end + 1:].strip()

        # print('Positive tags:', positive_tags_string)
        # print('Negative tags:', negative_tags_string)
        # print('Extra data:', extra_data_string)

        positive_tags_raw = positive_tags_string.replace('\n', ',').split(',')
        negative_tags_raw = negative_tags_string.replace('\n', ',').split(',')

        positive_tags = [tag.strip() for tag in positive_tags_raw if tag.strip() != '']
        negative_tags = [tag.strip() for tag in negative_tags_raw if tag.strip() != '']

        return positive_tags, negative_tags, extra_data_string

    @staticmethod
    def tags_list_to_tag_data(tags: [str]) -> dict:
        data_tag = []
        data_weight = []
        for tag in tags:
            raw_tags, tag_weights = Prompts.analysis_tag(tag)
            if len(raw_tags) == 0:
                continue
            for raw_tag, tag_weight in zip(raw_tags, tag_weights):
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
        if tag.startswith('['):
            raw_tag, weight = parse_wrapper(tag, '[', ']', 0.9)
            tag_list.append(raw_tag)
            weight_list.append(weight)
        elif tag.startswith('{'):
            raw_tag, weight = parse_wrapper(tag, '{', '}', 1.1)
            tag_list.append(raw_tag)
            weight_list.append(weight)
        elif tag.startswith('('):
            if ':' in tag:
                sub_tags = tag.replace('(', '').replace(')', '').split(':')
                for sub_tag in sub_tags:
                    weight = try_float(sub_tag)
                    if weight:
                        weight_list.append(weight)
                    else:
                        tag_list.append(sub_tag)
            else:
                raw_tag, weight = parse_wrapper(tag, '(', ')', 1.1)
                tag_list.append(raw_tag)
                weight_list.append(weight)
        elif tag.startswith('<'):
            sub_tags = tag.replace('<', '').replace('>', '').split(':')

            weight = try_float(sub_tags[2]) if len(sub_tags) > 2 else None
            weight = 1.0 if weight is None else weight
            raw_tag = sub_tags[0] + ':' + sub_tags[1] if len(sub_tags) > 1 else sub_tags[0]

            tag_list.append(raw_tag)
            weight_list.append(weight)
        else:
            tag_list.append(tag)
            weight_list.append(1.0)

        return tag_list, weight_list


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


