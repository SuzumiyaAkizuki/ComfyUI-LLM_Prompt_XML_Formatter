import re
import os
import json

# 默认风格库
DEFAULT_STYLES = {
    "Example": {
        "artist": "ciloranko,ask \\(askzy\\),diyokama,quasarcake,remsrar,modare,liuyunnnn",
        "style": "**ultimate masterpiece digital painting**, , **ethereal lighting**, **dreamy aesthetic**, **delicate floral details**, **high saturation blue sky**,**expressionist brushwork and high textural detail**,**maximalist detail**, **painterly texture**,oil painting,stunning aesthetic, ultra-detailed cross-hatching, extreme high contrast, dynamic line art"
    }
}


class LLM_Xml_Style_Injector:
    def __init__(self):
        self.styles = DEFAULT_STYLES
        # 加载styles.json
        self.json_path = os.path.join(os.path.dirname(__file__), "styles.json")
        if os.path.exists(self.json_path):
            try:
                with open(self.json_path, 'r', encoding='utf-8') as f:
                    file_styles = json.load(f)
                    self.styles.update(file_styles)
            except Exception as e:
                print(f"Failed to load styles.json: {e}")

    @classmethod
    def INPUT_TYPES(s):
        style_keys = list(DEFAULT_STYLES.keys())
        json_path = os.path.join(os.path.dirname(__file__), "styles.json")
        if os.path.exists(json_path):
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for k in data.keys():
                        if k not in style_keys:
                            style_keys.append(k)
            except:
                pass

        return {
            "required": {
                "xml_input": ("STRING", {"forceInput": True}),
                "preset": (style_keys,),
            },
            "optional": {
                "artist_add": ("STRING", {
                    "multiline": True,
                    "default": "",
                    "placeholder": "Add extra artists here (comma separated). Will be added BEFORE the preset."
                }),
                "style_add": ("STRING", {
                    "multiline": True,
                    "default": "",
                    "placeholder": "Add extra styles here (comma separated). Will be added BEFORE the preset."
                }),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("xml_output",)
    FUNCTION = "inject_style"
    CATEGORY = "LLM XML Helpers"

    def inject_style(self, xml_input, preset, artist_add, style_add):
        current_styles = self.styles
        if os.path.exists(self.json_path):
            try:
                with open(self.json_path, 'r', encoding='utf-8') as f:
                    current_styles.update(json.load(f))
            except:
                pass

        selected_data = current_styles.get(preset, {"artist": "", "style": ""})

        preset_artist = selected_data.get("artist", "")
        preset_style = selected_data.get("style", "")

        # 处理 Artist
        parts_artist = [artist_add.strip(), preset_artist]
        # 过滤掉空字符串，然后用逗号连接
        target_artist = ", ".join([p for p in parts_artist if p])

        # 处理 Style
        parts_style = [style_add.strip(), preset_style]
        target_style = ", ".join([p for p in parts_style if p])

        output_text = xml_input


        def upsert_tag(text, tag_name, content, insert_after_tag=None):
            """
            text: 完整的 XML 文本
            tag_name: 比如 "artist" 或 "style"
            content: 要填入的内容
            insert_after_tag: 如果当前标签不存在，尝试寻找这个标签并插在它后面 (比如 "style")
            """
            if not content:
                # 如果内容是空的，就不折腾了，直接返回
                return text

            tag_pattern = f"(<{tag_name}>)(.*?)(</{tag_name}>)"

            if re.search(tag_pattern, text, re.DOTALL | re.IGNORECASE):

                return re.sub(tag_pattern, f"\\1{content}\\3", text, flags=re.DOTALL | re.IGNORECASE)

            else:
                new_block = f"<{tag_name}>{content}</{tag_name}>"

                if insert_after_tag:
                    target_pattern = f"(</{insert_after_tag}>)"
                    if re.search(target_pattern, text, re.IGNORECASE):
                        print(f"ℹ️ Auto-inserting <{tag_name}> after <{insert_after_tag}>")
                        return re.sub(target_pattern, f"\\1\n{new_block}", text, flags=re.IGNORECASE, count=1)

                # 如果没有依托点，或者依托点也没找到，就插在整个字符串最后
                print(f"⚠️ Missing tag <{tag_name}>, appending to end.")
                return text + "\n" + new_block

        # 执行 Style
        output_text = upsert_tag(output_text, "style", target_style)

        # 执行 Artist
        output_text = upsert_tag(output_text, "artist", target_artist, insert_after_tag="style")

        # 调试打印
        print(f"\n--- Style Injected ---\nFinal Artist: {target_artist[:50]}...\nFinal Style: {target_style[:50]}...\n")

        return (output_text,)
