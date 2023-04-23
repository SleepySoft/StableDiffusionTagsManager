from collections import OrderedDict

from TagManager import PRIMARY_KEY, DATABASE_SUPPORT_FIELD, DATABASE_FIELDS


BACKUP_LIMIT = 20
PUBLIC_DATABASE = 'public.csv'
PRIVATE_DATABASE = 'private.csv'

ANALYSIS_DISPLAY_FIELD = [PRIMARY_KEY, 'weight', 'path', 'value', 'translate_cn', 'comments']

ANALYSIS_SHOW_COLUMNS = OrderedDict()
for f in ANALYSIS_DISPLAY_FIELD:
    ANALYSIS_SHOW_COLUMNS[f] = DATABASE_SUPPORT_FIELD[f]
ANALYSIS_SHOW_COLUMNS['weight'] = '权重'

PRESET_TAG_PATH = ['正向效果', '反向效果', '中立效果', '低价值',
                   '场景/室外', '场景/室内', '场景/幻境', '场景/道具', '场景/光影',
                   '角色/女性', '角色/男性', '角色/福瑞',
                   '脸部/头发', '脸部/眼睛', '脸部/嘴巴', '脸部/表情', '脸部/其它',
                   '人物/身体', '人物/服饰', '人物/饰品', '人物/动作', '人物/感觉', '人物/人种',
                   '视角', '图片风格', '18x', '非通用描述', '玄学？']

ANALYSIS_README = """使用说明：
1. 将tags粘贴到左边的输入框中。第一行为正面tag，第二行为负面tag，忽略空行以及三行之后的附加数据。可以直接粘贴从C站上复制下来的图片参数。
2. 下方左侧列表显示正面tag分析结果，右侧列表显示负面tag分析结果。如果数据库中有对应tag的数据，则展示更多信息，否则除权重外显示空白。
   注：仅能分析基本的tag权重，对于特殊tag格式（过渡，LoRA）的分析并不完善。
3. 下方中间的树形控件显示预置及数据库中已存在的tag分组，将两侧的tag（可以多选）拖到分组结点上可以将tag快速分组并加入数据库。
4. 双击tag列表可以编辑该tag的详细信息，点击确定后该tag信息会更新到数据库。
   注：如果不对新tag进行3或4的操作，则这个tag不会放入数据库。建议只把有用的tag加入数据库。你也可以通过excel修改数据库的csv文件。
"""
