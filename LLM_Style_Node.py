import os
import json
import re
import difflib
from lxml import etree


class BColors:
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'


# 预定义默认样式
DEFAULT_STYLES = {
    "空样式，请在下方文本框中自行书写": {
        "artist": "",
        "style": ""
    }
}

CONFIG_FILENAME = "LPF_config.json"
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), CONFIG_FILENAME)


def load_styles_from_config():
    """读取配置文件并与默认样式合并"""
    styles = DEFAULT_STYLES.copy()

    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
                user_styles = data.get("styles", {})
                if isinstance(user_styles, dict) and user_styles:
                    styles.update(user_styles)
        except Exception as e:
            print(f"{BColors.FAIL}[XML_Style_Injector]: 加载配置文件出错: {e}{BColors.ENDC}")

    return styles


class LLM_Xml_Style_Injector:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(s):
        # 获取最新的 style 表
        current_styles = load_styles_from_config()
        style_keys = list(current_styles.keys())

        return {
            "required": {
                "xml_input": ("STRING", {"forceInput": True}),
                "preset": (style_keys,),
            },
            "optional": {
                "artist_add": ("STRING", {
                    "multiline": True,
                    "default": "",
                    "placeholder": "在此输入要添加的 Artist，将拼接到预设前面"
                }),
                "style_add": ("STRING", {
                    "multiline": True,
                    "default": "",
                    "placeholder": "在此输入要添加的 Style，将拼接到预设前面"
                }),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("xml_output",)
    FUNCTION = "inject_style"
    CATEGORY = "NewBie LLM Formatter"

    def inject_style(self, xml_input, preset, artist_add, style_add):
        current_styles = load_styles_from_config()
        selected_data = current_styles.get(preset, {"artist": "", "style": ""})

        preset_artist = selected_data.get("artist", "").strip()
        preset_style = selected_data.get("style", "").strip()

        # 拼接
        def combine_tags(input_val, preset_val):
            input_val = input_val.strip()
            if input_val and preset_val:
                return f"{input_val}, {preset_val}"
            return input_val if input_val else preset_val

        target_artist = combine_tags(artist_add, preset_artist)
        target_style = combine_tags(style_add, preset_style)

        # 提取 XML
        match = re.search(r'(<img>.*?</img>)', xml_input, re.DOTALL | re.IGNORECASE)

        if not match:
            print(f"{BColors.WARNING}[LLM_Prompt_Formatter]: 未发现 <img> 标签，跳过注入。{BColors.ENDC}")
            return (xml_input,)

        header_text = xml_input[:match.start()].strip()
        xml_content = match.group(1)

        try:
            # 解析
            parser = etree.XMLParser(recover=True, encoding='utf-8')
            root = etree.fromstring(xml_content.encode('utf-8'), parser=parser)

            # 更新或创建标签
            def upsert(parent, tag_name, text_value):
                if text_value and text_value.strip():
                    elements = parent.xpath(f"//{tag_name}")
                    if elements:
                        for el in elements:
                            el.text = text_value
                    else:
                        # 尝试找 general_tags 容器插入
                        print(f"{BColors.WARNING}[LLM_Prompt_Formatter]: 未找到<{tag_name}>标签，正在尝试注入<general_tags>{BColors.ENDC}")
                        gen_containers = parent.xpath("//general_tags")
                        if gen_containers:
                            new_node = etree.SubElement(gen_containers[0], tag_name)
                            new_node.text = text_value
                        else:
                            # 实在没地方插了就插在根节点最后
                            print(f"{BColors.WARNING}[LLM_Prompt_Formatter]: 未找到<general_tags>标签{BColors.ENDC}")
                            new_node = etree.SubElement(parent, tag_name)
                            new_node.text = text_value
                else:
                    print(f"{BColors.WARNING}[LLM_Prompt_Formatter]: 用户未输入<{tag_name}>，不改变标签{BColors.ENDC}")
                    pass


            upsert(root, "artist", target_artist)
            upsert(root, "style", target_style)

            modified_xml = etree.tostring(root, encoding='unicode', method='xml', pretty_print=True)
            modified_xml = repair_xml_custom(modified_xml)

            final_output = f"{header_text}\n{modified_xml}" if header_text else modified_xml
            return (final_output,)

        except Exception as e:
            print(f"{BColors.FAIL}[LLM_Prompt_Formatter]: XML 解析失败: {e}{BColors.ENDC}")
            return (xml_input,)


def repair_xml_custom(xml_string):
    """
    修复 XML 格式错误，不包含 XML 声明。
    成功修复时打印差异，修复失败时发出警告并返回原串。
    """
    if not xml_string.strip():
        return xml_string

    # 解析器
    strict_parser = etree.XMLParser(remove_blank_text=True)
    recover_parser = etree.XMLParser(recover=True, remove_blank_text=True)

    try:
        # 严格解析
        etree.fromstring(xml_string.encode('utf-8'), parser=strict_parser)
        print("[LLM_Prompt_Formatter]:已完成xml格式检查，无错误。")
        return xml_string
    except etree.XMLSyntaxError:
        try:
            # 修复
            root = etree.fromstring(xml_string.encode('utf-8'), parser=recover_parser)
            if root is None:
                raise ValueError("无法解析出任何有效结构")

            repaired_xml = etree.tostring(
                root,
                encoding='unicode',
                pretty_print=True,
                xml_declaration=False
            ).strip()

            # 修复对比
            print(f"{BColors.WARNING}[LLM_Prompt_Formatter]:检测到xml格式错误，已自动修复。差异如下：{BColors.ENDC}")
            diff = difflib.unified_diff(
                xml_string.splitlines(),
                repaired_xml.splitlines(),
                fromfile='Original',
                tofile='Repaired',
                lineterm=''
            )

            has_diff = False
            for line in diff:
                if line.startswith(('+', '-')) and not line.startswith(('+++', '---')):
                    print(line)
                    has_diff = True

            if not has_diff:
                print("(仅修复了微小的空白符或内部编码格式)")

            print("-" * 30)
            return repaired_xml

        except Exception as e:
            # 修复失败
            print(f"{BColors.WARNING}[LLM_Prompt_Formatter]:XML 损坏严重，无法修复！必要时请停止工作流。\n错误详情: {e}{BColors.ENDC}")
            print("-" * 30)
            return xml_string