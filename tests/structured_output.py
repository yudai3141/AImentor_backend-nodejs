# import json
# from openai import OpenAI
# from dotenv import load_dotenv


# # 環境変数のロード
# load_dotenv()

# client = OpenAI()

# text="日本の総理大臣"

# response1 = client.chat.completions.create(
#     model="gpt-4o",
#     messages=[{"role": "user", "content": f"{text}について教えて"}],
#     response_format={
#         "type": "json_schema",
#         "json_schema": {
#             "name": "prime_minister",
#             "schema": {
#                 "type": "object",
#                 "properties": {
#                     "name": {"type": "string"},
#                     "age": {"type": "number"},
#                     "history": {"type": "string"},
#                 },
#                 "required": ["name", "age", "history"],
#                 "additionalProperties": False,
#             },
#             "strict": True,
#         },
#     },
# )

# response = json.loads(response1.choices[0].message.content)
# print(response)

# name = response["name"]
# print(type(name),name)


###### text情報の抽出 #############

# from pydantic import BaseModel
# from openai import OpenAI
# from dotenv import load_dotenv

# # 環境変数のロード
# load_dotenv()

# client = OpenAI()

# class CalendarEvent(BaseModel):
#     name: str
#     date: str
#     participants: list[str]

# completion = client.beta.chat.completions.parse(
#     model="gpt-4o-2024-08-06",
#     messages=[
#         {"role": "system", "content": "Extract the event information."},
#         {"role": "user", "content": "Alice and Bob are going to a science fair on Friday."},
#     ],
#     response_format=CalendarEvent,
# )

# event = completion.choices[0].message.parsed

# print(event)

from pydantic import BaseModel
from openai import OpenAI
from dotenv import load_dotenv

# 環境変数のロード
load_dotenv()

client = OpenAI()

class ShortTermGoal(BaseModel):
    shortTermGoals: list[str]

class ShortTermGoalItem(BaseModel):
    KPI: str
    numerical: bool
    tasks: list[str]


completion1 = client.beta.chat.completions.parse(
    model="gpt-4o",
    messages=[
        {"role": "system", "content": "あなたはユーザーの自己成長を促すAI上司です"},
        {"role": "user", "content": f"""
        あなたは、会社の上司の役割を持つアシスタントです。ユーザーが何も知らない前提で、『大目標: バックエンドエンジニアになる 』から2,3つの小目標を生成するプロセスを全面的にリードしてください。大目標は1カ月間の想定です。
        プロセスは以下の手順で行います：
        1. 大目標に対して、どのような小目標が考えられるかをユーザーに尋ねる。
        2. ユーザーが提示した小目標が不十分(すぐに達成可能または大目標からの関連性が不明)な場合もしくは1つしかない場合、新たに小目標をユーザーに尋ねる。ユーザーが行き詰まっていれば、小目標を提案する。
        3. 提示した小目標を踏まえて、ユーザーに決定させる。
        上記の結果、十分な小目標に分割できれば、ユーザーに確認し、okであればプロセスを終了する。
        """},
    ],
    response_format=ShortTermGoal,
)

ShortTermGoals = completion1.choices[0].message.parsed

print(ShortTermGoals)
print(f"type: {type(ShortTermGoals)}")

# # UI上に、『まずは~つ目の小目標について話しましょう。』のような内容を表示

# # 各小目標について、以下の内容を行う
# completion2 = client.beta.chat.completions.parse(
#     model="gpt-4o",
#     messages=[
#         {"role": "system", "content": "あなたはユーザーの自己成長を促すAI上司です"},
#         {"role": "user", "content": f"""
#         あなたは、会社の上司の役割を持つアシスタントです。ユーザーの『小目標: {ShortTermGoals[0]} 』のKPI決定,要素分解プロセスを全面的にリードしてください。
#         1. 小目標に対して、達成したいKPIをユーザーに尋ねる。
#         2. ユーザーが提示したKPIについて、達成率が数値的に評価できる数値基準であるか、達成率をtrueかfalseのどちらかで表すTF目標であるかを、あなたが判断する。
#         (数値基準目標の例は「~個達成する」「~%向上させる」といったもので、TF目標の例は「~できるようになる」といったもの)
#         3. TF目標であると判断した場合、それをさらに最小の仕事単位「タスク」に分割する。数値基準目標であると判断した場合はタスク分割を行わない。
#         4. TF目標のタスク分割を行う場合、**1つ1つのタスクは明確かつ単純なTFタスクにしてください**
#         5. 上記の確認がOKであれば終了し、問題があればその理由を考慮してKPI設定、タスク設定に戻る。
#         上記の結果、十分なタスクに分割できれば、ユーザーに確認し、okであればプロセスを終了する。
#         """},
#     ],
#     response_format=ShortTermGoalItem,
# )



