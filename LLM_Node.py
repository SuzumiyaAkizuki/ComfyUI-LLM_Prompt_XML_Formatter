import os
import re
import json
from openai import OpenAI

class BColors:
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m' # Reset all attributes

CONFIG_FILENAME = "LPF_config.json"
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), CONFIG_FILENAME)


def load_api_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"{BColors.FAIL}[LLM_Prompt_Formatter]: Error loading {CONFIG_FILENAME}: {e} {BColors.ENDC}")
    return {}


class LLM_Prompt_Formatter:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(s):
        config = load_api_config()
        model_list = config.get("model_list", [])
        api_key = config.get("api_key")
        api_url = config.get("api_url")
        if model_list and isinstance(model_list, list) and api_key and isinstance(api_key, str) and api_url and isinstance(api_url, str):
            model_widget = (model_list,)
        else:
            model_widget = ("STRING", {"multiline": False, "default": "gpt-4o"})
            print(f"{BColors.WARNING}[LLM_Prompt_Formatter]: 读取API失败，请检查配置文件。你可以在节点输入相关信息。请注意，你的APIKEY会在原图中保存。{BColors.ENDC}")


        return {
            "required": {
                "api_key": ("STRING", {"multiline": False, "default": "sk-...", "dynamicPrompts": False}),
                "api_url": ("STRING",
                            {"multiline": False, "default": "https://api.openai.com/v1", "dynamicPrompts": False}),
                "model_name": model_widget,
                "user_text": ("STRING",
                              {"multiline": True, "default": "1girl, holding a sword", "dynamicPrompts": False}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("xml_out", "text_out")
    FUNCTION = "process_text"
    CATEGORY = "LLM XML Helpers"

    def process_text(self, api_key, api_url, model_name, user_text):
        # 1. 加载配置（优先从 JSON 取，UI 次之）
        config = load_api_config()
        final_key = config.get("api_key") if config.get("api_key") else api_key
        final_url = config.get("api_url") if config.get("api_url") else api_url

        # 2. 从 JSON 获取 System Prompt
        # 如果 JSON 里没写这个字段，就给它一个默认的，防止代码崩掉
        system_content = config.get("system_prompt", "You are a helpful assistant that provides prompt tags.")
        gemma_prompt = config.get("gemma_prompt", "You are an assistant designed to generate high-quality anime images with the highest degree of image-text alignment based on xml format textual prompts. <Prompt Start>\n");


        # 3. 初始化并调用 OpenAI
        try:
            if not final_key or final_key == "sk-...":
                print(f"{BColors.FAIL}[LLM_Prompt_Formatter]: API KEY 缺失！请在 LPF_config.json 中配置。{BColors.ENDC}")
                return ("API KEY 缺失！请在 LPF_config.json 中配置", "API KEY Missing")

            client = OpenAI(api_key=final_key, base_url=final_url)
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_content},
                    {"role": "user", "content": user_text}
                ],
                temperature=0.7,
            )
            full_response = response.choices[0].message.content
            # XML 匹配，不成功则触发中英分离
            xml_pattern = r"```xml\s*(.*?)\s*```"
            match = re.search(xml_pattern, full_response, re.DOTALL)

            if match:
                xml_content = match.group(1).strip()
                # 剩下的部分作为 text_out
                text_content = full_response.replace(match.group(0), "").strip()
            else:
                print(f"{BColors.WARNING}[LLM_Prompt_Formatter]: 解析代码块失败，正在尝试语义分离{BColors.ENDC}")
                # 提取非中文作为 xml_out
                xml_content = re.sub(r'[\u4e00-\u9fff]+', '', full_response).strip()

                # 提取中文作为 text_out
                chinese_blocks = re.findall(r'[\u4e00-\u9fff\u3000-\u303f\uff00-\uffef\s]+', full_response)
                text_content = "".join(chinese_blocks).strip() or "模型未提供中文说明。"

            xml_content=clean_prompt(xml_content,gemma_prompt)
            return (xml_content, text_content)

        except Exception as e:
            print(f"{BColors.FAIL}[LLM_Prompt_Formatter]: {str(e)}, 请确认 API 配置是否正确。{BColors.ENDC}")
            raise RuntimeError(f"LLM_Prompt_Formatter failed: {str(e)}") from e



def clean_prompt(xml_content,gemma_prompt):
    """
    清洗大模型生成的 XML 提示词
    添加gemma_prompt
    """

    # 预定义的gemma system prompt
    header = gemma_prompt
    # 使用正则匹配最外层的 { ... }
    match = re.search(r'(\{.*\})', xml_content, re.DOTALL)

    if not match:
        print(f"{BColors.WARNING}[LLM_Prompt_Formatter]: LLM返回结果匹配失败，请检查输出结果，必要时停止工作流。{BColors.ENDC}")
        return xml_content

    # 获取大括号及其内部的内容
    json_part = match.group(1)

    cleaned_content = f"{header}\n{json_part}"

    return cleaned_content