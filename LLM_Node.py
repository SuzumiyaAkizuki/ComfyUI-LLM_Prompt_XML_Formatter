import os
import folder_paths
import re
from openai import OpenAI


class LLM_Prompt_Formatter:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "api_key": ("STRING", {
                    "multiline": False,
                    "default": "sk-...",
                    "dynamicPrompts": False
                }),
                "api_url": ("STRING", {
                    "multiline": False,
                    "default": "https://api.openai.com/v1",
                    "dynamicPrompts": False
                }),
                "model_name": ("STRING", {
                    "multiline": False,
                    "default": "gpt-4o",
                    "dynamicPrompts": False
                }),
                "user_text": ("STRING", {
                    "multiline": True,
                    "default": "1girl, holding a sword",
                    "dynamicPrompts": False
                }),
            },
        }

    RETURN_TYPES = ("STRING","STRING")
    RETURN_NAMES = ("xml_out", "text_out")
    FUNCTION = "process_text"
    CATEGORY = "LLM XML Helpers"

    def process_text(self, api_key, api_url, model_name, user_text):
        # 读取system prompt
        current_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(current_dir, "system prompt.txt")

        system_content = ""

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                system_content = f.read()
        except FileNotFoundError:
            # 找不到system prompt
            return (f"Error: 找不到系统提示词文件: {file_path}。请确保目录下有 system prompt.txt 文件。",)
        except Exception as e:
            return (f"Error: 读取文件出错: {str(e)}",)

        # 初始化 OpenAI 客户端
        try:
            client = OpenAI(
                api_key=api_key,
                base_url=api_url
            )

            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_content},
                    {"role": "user", "content": user_text}
                ],
                temperature=0.7,
            )
            full_response = response.choices[0].message.content
            pattern = r"```xml\s*(.*?)\s*```"
            match = re.search(pattern, full_response, re.DOTALL)
            if match:
                # 提取出XML内容
                xml_content = match.group(1).strip()
                # 提取出解释说明内容
                text_content = full_response.replace(match.group(0), "").strip()
            else:
                print("警告: 未检测到 XML 代码块，直接原样输出")
                xml_content = full_response
                text_content = "未检测到格式化 XML，请检查 LLM 输出。"

            return (xml_content, text_content)


        except Exception as e:
            return (f"API Error: {str(e)}",)
