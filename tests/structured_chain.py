import os
from dotenv import load_dotenv
from langchain_openai.chat_models import ChatOpenAI
import json

# 環境変数のロード
load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")

llm = ChatOpenAI(
    model_name="gpt-4o",
    openai_api_key=openai_api_key
)

# 関数の定義
function_get_language = {
    "name": "get_recommended_language",
    "description": "特定の職業に一番おすすめのプログラミング言語を取得します",
    "parameters": {
        "type": "object",
        "properties": {
            "programming_language": {
                "type": "string",
                "description": "おすすめのプログラミング言語の名前"
            }
        },
        "required": ["programming_language"]
    }
}

function_get_advice = {
    "name": "get_learning_advice",
    "description": "プログラミング言語を学ぶための3ステップのアドバイスを提供します",
    "parameters": {
        "type": "object",
        "properties": {
            "advice": {
                "type": "string",
                "description": "3ステップのアドバイス、各ステップは短く具体的に"
            }
        },
        "required": ["advice"]
    }
}

# ユーザーからの入力
job = "データサイエンティスト"

# 最初のステップ：おすすめのプログラミング言語を取得
prompt_1 = f"{job}に一番オススメのプログラミング言語は何ですか？"

response_1 = llm.predict_messages(
    messages=[{"role": "user", "content": prompt_1}],
    functions=[function_get_language],
    function_call={"name": "get_recommended_language"}
)

# 関数呼び出しの結果を取得
function_call_1 = response_1.additional_kwargs.get("function_call", {})
arguments_1 = function_call_1.get("arguments", "{}")
language_data = json.loads(arguments_1)
programming_language = language_data.get("programming_language", "")

print("1個目の結果：")
print(programming_language)
# print(f"responce:{response_1}")

# 2つ目のステップ：アドバイスを取得
prompt_2 = f"{programming_language}を学ぶためにやるべきことを3ステップで100文字で教えて。"

response_2 = llm.predict_messages(
    messages=[{"role": "user", "content": prompt_2}],
    functions=[function_get_advice],
    function_call={"name": "get_learning_advice"}
)

# 関数呼び出しの結果を取得
function_call_2 = response_2.additional_kwargs.get("function_call", {})
arguments_2 = function_call_2.get("arguments", "{}")
advice_data = json.loads(arguments_2)
advice = advice_data.get("advice", "")

print("2個目の結果：")
print(advice)
