import sys
import json
import os
import re
from dotenv import load_dotenv
from langchain.chat_models import ChatOpenAI
from pydantic import BaseModel
from langchain.schema import SystemMessage, HumanMessage, AIMessage
from openai import OpenAI

class ShortTermGoal(BaseModel):
    shortTermGoals: list[str]

class ShortTermGoalItem(BaseModel):
    shortTerm_goal: str
    KPI: str
    numerical_or_TF: str
    KPI_indicator: int

class ShortTermGoalItemCompleted(BaseModel):
    shortTerm_goal: str
    KPI: str
    numerical_or_TF: str
    KPI_indicator: int
    tasks: list[str]

def main():
    # 環境変数をロード
    load_dotenv()
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        print('Error: OPENAI_API_KEY is not set.', file=sys.stderr)
        sys.exit(1)

    client = OpenAI(api_key=openai_api_key)
    # ChatOpenAIのインスタンスを作成
    chat = ChatOpenAI(
        temperature=0,
        model="gpt-4o",  # 必要に応じてモデルを変更
        openai_api_key=openai_api_key
    )

    # 標準入力からJSON形式のデータを受け取る
    
    data = {
    "subGoals": [
        {
            "subGoal": "基本的なRESTful APIを設計し、実装する。",
        },
        {
            "subGoal": "簡単なデータベーススキーマを設計し、SQLを使って実装する。",
        }
    ],
    "goal_num": 1,
    "stage": 2,
    "messages": [{"role": "user", "content": "APIを3つ作成する"}],
    "session_messages": [
        {
            "role": "system",
            "content": "\nあなたは、会社の上司の役割を持つアシスタントです。ユーザーが何も知らない前提で、大目標から2,3つの小目標を生成するプロセスを全面的にリードしてください。\n小目標は1カ月間の想定です。\nプロセスは以下の手順で行います：\n1. 大目標に対して、どのような小目標が考えられるかをユーザーに尋ねる。\n2. ユーザーが提示した小目標が不十分(すぐに達成可能または大目標からの関連性が不明)な場合もしくは1つしかない場合、新たに小目標をユーザーに尋ねる。ユーザーが行き詰まっていれば、小目標を提案する。\n3. 提示した小目標を踏まえて、ユーザーに決定させる。\nすべてのプロセスが終了後、'小目標の設定が完了しました'と出力してください。\n"
        },
        {
            "role": "user",
            "content": "大目標は「バックエンドエンジニアです」"
        },
        {
            "role": "assistant",
            "content": "バックエンドエンジニアになるための小目標として、どのようなものが考えられるでしょうか？いくつかアイデアを出してみてください。"
        },
        {
            "role": "user",
            "content": "api開発、db設計"
        },
        {
            "role": "assistant",
            "content": "良いスタートですね！「API開発」と「DB設計」はバックエンドエンジニアになるための重要なスキルです。ただし、これらの小目標を1カ月で達成するためには、もう少し具体的にする必要があります。\n\n例えば、「API開発」については「基本的なRESTful APIを設計し、実装する」といった具体的な目標にすることができます。「DB設計」については「簡単なデータベーススキーマを設計し、SQLを使って実装する」といった形です。\n\nこれらを踏まえて、もう一度小目標を考えてみてください。もしくは、他に追加したい小目標があれば教えてください。"
        },
        {
            "role": "user",
            "content": "上記で大丈夫です"
        },
        {
            "role": "assistant",
            "content": "了解しました。それでは、以下の2つの小目標で進めていきましょう。\n\n1. 基本的なRESTful APIを設計し、実装する。\n2. 簡単なデータベーススキーマを設計し、SQLを使って実装する。\n\nこの2つの小目標でよろしいですか？それとも、何か変更や追加がありますか？"
        },
        {
            "role": "user",
            "content": "okです"
        },
        {
            "role": "assistant",
            "content": "ありがとうございます。それでは、小目標の設定が完了しました。これらの小目標を達成するために、計画的に取り組んでいきましょう。何かサポートが必要な場合は、いつでもお知らせください。\n\n次のステップとして、最初の目標である「基本的なRESTful APIを設計し、実装する。」について、KPIを話し合いましょう。どのようなものが考えられるでしょうか？"
        }
    ]
}

    try:
        messages = data.get('messages', [])
        session_messages = data.get('session_messages', [])
        stage = data.get('stage', 1)
        goal_num = data.get('goal_num', 1)
        sub_goals = data.get('subGoals', [])
        TF_index = data.get('TF_index', 0)
    except json.JSONDecodeError:
        print('Error: Invalid JSON input.', file=sys.stderr)
        sys.exit(1)

    # セッション内のメッセージ履歴がなければ初期化
    if not session_messages:
        session_messages = [SystemMessage(content=initial_system_message_content())]
    else:
        # セッションメッセージを適切なMessageオブジェクトに変換
        session_messages = convert_to_langchain_messages(session_messages)

    # 新しいメッセージを適切なMessageオブジェクトに変換
    user_messages = convert_to_langchain_messages(messages)

    result = {}  # 返却する結果
    result["subGoals"] = sub_goals
    result["goal_num"] = goal_num

    if stage == 1:
        try:
            # チャットメッセージを更新
            chat_messages = session_messages + user_messages
            # OpenAI APIを呼び出す
            response = chat(chat_messages)
            gpt_message = response.content

            # サブ目標を生成
            if '小目標の設定が完了しました。' in gpt_message:
                try:
                    completion1 = client.beta.chat.completions.parse(
                        model="gpt-4o",
                        messages=[
                            {"role": "system", "content": "あなたの仕事は、文章の要約です"},
                            {"role": "user", "content": f"""
                            {chat_messages}
                            上記の会話ログから、小目標をリスト形式で出力してください。
                            """},
                        ],
                        response_format=ShortTermGoal,
                    )
                    gpt_message += f"\n次のステップとして、最初の目標である{completion1.choices[0].message.parsed.shortTermGoals[0]}について、KPIを話し合いましょう。どのようなものが考えられるでしょうか？"
                    result = {'response': gpt_message}
                    result['subGoals'] = [{"subGoal": completion1_item} for completion1_item in completion1.choices[0].message.parsed.shortTermGoals] #resultの"subGoals"内に{"subgoal": ~}を追加する
                    result['stage'] = 2  # 次のステージに進む

                except Exception as e:
                    error_message = f'OpenAI API Error: {str(e)}, stage 1 → 2'
                    print(json.dumps({'error': error_message}), file=sys.stderr)
                    sys.exit(1)
            else:
                chat_messages.append(AIMessage(content=gpt_message))
                result = {'response': gpt_message}
                    
            # セッションメッセージを保存
            result['session_messages'] = [message_to_dict(m) for m in chat_messages]

            # 結果をJSONで出力
            print(json.dumps(result, ensure_ascii=False))
            sys.exit(0)

        except Exception as e:
            error_message = f'OpenAI API Error: {str(e)}, stage 1'
            print(json.dumps({'error': error_message}), file=sys.stderr)
            sys.exit(1)
    
    elif stage == 2: #小目標のKPI設定,numerical判定の初回
        chat_messages = session_messages + [SystemMessage(content=third_system_message_content(sub_goals[goal_num - 1]))]

        try:
            result['stage'] = 3  # 次のステージに進む準備
            chat_messages += user_messages

            # OpenAI APIを呼び出す
            response = chat(chat_messages)
            gpt_message = response.content

            if 'KPI設定・目標分類が完了しました' in gpt_message:
                try:
                    completion2 = client.beta.chat.completions.parse(
                        model="gpt-4o",
                        messages=[
                            {"role": "system", "content": "あなたの仕事は、文章の要約です"},
                            {"role": "user", "content": f"""
                            {chat_messages}
                            上記の会話ログから、小目標、KPI、numerical_or_TF、KPI_indicatorをリスト形式で出力してください。
                            """},
                        ],
                        response_format=ShortTermGoalItem,
                    )

                    result["subGoals"][goal_num - 1] = completion2.choices[0].message.parsed.dict()
                    
                    goal_num += 1 #次の小目標
                    result["goal_num"] += 1
                    if goal_num - 1 >= len(sub_goals):
                        # KPI設定終了
                        chat_messages.append(AIMessage(content=gpt_message))
                        result['stage'] = 4
                        result["response"] = gpt_message
                    else:
                        gpt_message += f"\n次のステップとして、目標：「{sub_goals[goal_num - 1]["subGoal"]}」について、KPIを話し合いましょう。どのようなものが考えられるでしょうか？"
                        chat_messages.append(AIMessage(content=gpt_message))
                        result['stage'] = 3
                        result["response"] = gpt_message

                    result['session_messages'] = [message_to_dict(m) for m in chat_messages]
                    result["response"] = gpt_message
                    print(json.dumps(result, ensure_ascii=False))
                    sys.exit(0)

                except Exception as e:
                    error_message = f'OpenAI API Error: {str(e)}, stage 2'
                    print(json.dumps({'error': error_message}), file=sys.stderr)
                    sys.exit(1)
                    
            else:
                gpt_message = response.content
                chat_messages.append(AIMessage(content=gpt_message))
                # セッションメッセージを保存
                result['session_messages'] = [message_to_dict(m) for m in chat_messages]
                result["response"] = gpt_message

            # 結果をJSONで出力
            print(json.dumps(result, ensure_ascii=False))
            sys.exit(0)
            

        except Exception as e:
            error_message = f'OpenAI API Error: {str(e)}, stage 2'
            print(json.dumps({'error': error_message}), file=sys.stderr)
            sys.exit(1)
    
    elif stage == 3: #小目標のKPI設定,numerical判定
        try:
            chat_messages = session_messages + user_messages

            # OpenAI APIを呼び出す
            response = chat(chat_messages)
            gpt_message = response.content


            if 'KPI設定・目標分類が完了しました' in gpt_message:
                try:
                    completion2 = client.beta.chat.completions.parse(
                        model="gpt-4o",
                        messages=[
                            {"role": "system", "content": "あなたの仕事は、文章の要約です"},
                            {"role": "user", "content": f"""
                            {chat_messages}
                            上記の会話ログから、小目標、KPI、numerical_or_TF、KPI_indicatorをリスト形式で出力してください。
                            """},
                        ],
                        response_format=ShortTermGoalItem,
                    )

                    result["subGoals"][goal_num - 1] = completion2.choices[0].message.parsed.dict()
                    
                    goal_num += 1 #次の小目標
                    result["goal_num"] += 1
                    if goal_num - 1 >= len(sub_goals):
                        
                        # タスク分解の必要性を確認
                        is_TF_exist = False
                        first_TF_index = -1
                        for index, goal in enumerate(result["subGoals"]):
                            if goal.get("numerical_or_TF") == "TF":
                                is_TF_exist = True
                                first_TF_index = index
                                break

                        if is_TF_exist:
                            result["TF_index"] = first_TF_index
                            gpt_message += f"\n最後のステップとして、TF目標について、タスク分解を行いましょう。1つ目のTF目標：「{result["subGoals"][first_TF_index]["shortTerm_goal"]}」について、最小単位の仕事の単位であるタスクに分解していきましょう。どのようなタスクに分解できますか？"
                        else:
                            result["isTerminated"] = True

                        chat_messages.append(AIMessage(content=gpt_message))
                        result['stage'] = 4
                        result["response"] = gpt_message
                    else:
                        gpt_message += f"\n次のステップとして、目標：「{sub_goals[goal_num - 1]["subGoal"]}」について、KPIを話し合いましょう。どのようなものが考えられるでしょうか？"
                        chat_messages.append(AIMessage(content=gpt_message))
                        result['stage'] = 3
                        result["response"] = gpt_message

                    result['session_messages'] = [message_to_dict(m) for m in chat_messages]
                    result["response"] = gpt_message
                    print(json.dumps(result, ensure_ascii=False))
                    sys.exit(0)

                except Exception as e:
                    error_message = f'OpenAI API Error: {str(e)}, stage 2'
                    print(json.dumps({'error': error_message}), file=sys.stderr)
                    sys.exit(1)
                    
            else:
                gpt_message = response.content
                chat_messages.append(AIMessage(content=gpt_message))
                # セッションメッセージを保存
                result['session_messages'] = [message_to_dict(m) for m in chat_messages]
                result["response"] = gpt_message

                # 結果をJSONで出力
                print(json.dumps(result, ensure_ascii=False))
                sys.exit(0)
            

        except Exception as e:
            error_message = f'OpenAI API Error: {str(e)}, stage 2'
            print(json.dumps({'error': error_message}), file=sys.stderr)
            sys.exit(1)

    elif stage == 4:
        try:
            chat_messages = session_messages + [SystemMessage(content=forth_system_message_content(sub_goals[TF_index]["shortTerm_goal"]))]
            chat_messages += user_messages
            result['stage'] = 5  # 次のステージに進む準備

            # OpenAI APIを呼び出す
            response = chat(chat_messages)
            gpt_message = response.content

            if 'タスク分解が完了しました' in gpt_message:
                try:
                    completion3 = client.beta.chat.completions.parse(
                        model="gpt-4o",
                        messages=[
                            {"role": "system", "content": "あなたの仕事は、文章の要約です"},
                            {"role": "user", "content": f"""
                            {chat_messages}
                            上記の会話ログから、小目標、KPI、numerical_or_TF、KPI_indicator、分解タスクをリスト形式で出力してください。
                            """},
                        ],
                        response_format=ShortTermGoalItemCompleted,
                    )
                    result["subGoals"][TF_index] = completion3.choices[0].message.parsed.dict()

                    exist_next_TF = False #  他のTF目標が存在するか
                    for index, goal in enumerate(result["subGoals"]):
                        if (goal.get("numerical_or_TF") == "TF") and (index > TF_index):
                            exist_next_TF = True
                            next_TF_index = index
                            break
                    
                    if exist_next_TF:
                        result["TF_index"] = next_TF_index
                        gpt_message += f"次に、TF目標「{result["subGoals"][next_TF_index]["shortTerm_goal"]}」について、最小単位の仕事の単位であるタスクに分解していきましょう。どのようなタスクに分解できますか？"
                        chat_messages.append(AIMessage(content=gpt_message))

                    else:
                        result["isTerminated"] = True
                    
                    result["response"] = gpt_message
                    result['session_messages'] = [message_to_dict(m) for m in chat_messages]
                    print(json.dumps(result, ensure_ascii=False))
                    sys.exit(0)

                except Exception as e:
                    error_message = f'OpenAI API Error: {str(e)}, stage 2'
                    print(json.dumps({'error': error_message}), file=sys.stderr)
                    sys.exit(1)

            else:
                chat_messages.append(AIMessage(content=gpt_message))
                result["TF_index"] = TF_index
                result["response"] = gpt_message
                result['session_messages'] = [message_to_dict(m) for m in chat_messages]
                print(json.dumps(result, ensure_ascii=False))
                

        except Exception as e:
            error_message = f'OpenAI API Error: {str(e)}, stage 2'
            print(json.dumps({'error': error_message}), file=sys.stderr)
            sys.exit(1)

    elif stage == 5:
        try:
            chat_messages = session_messages + user_messages
            # OpenAI APIを呼び出す
            response = chat(chat_messages)
            gpt_message = response.content

            if 'タスク分解が完了しました' in gpt_message:
                try:
                    completion3 = client.beta.chat.completions.parse(
                        model="gpt-4o",
                        messages=[
                            {"role": "system", "content": "あなたの仕事は、文章の要約です"},
                            {"role": "user", "content": f"""
                            {chat_messages}
                            上記の会話ログから、小目標、KPI、numerical_or_TF、KPI_indicator、分解タスクをリスト形式で出力してください。
                            """},
                        ],
                        response_format=ShortTermGoalItemCompleted,
                    )
                    result["subGoals"][TF_index] = completion3.choices[0].message.parsed.dict()

                    exist_next_TF = False #  他のTF目標が存在するか
                    for index, goal in enumerate(result["subGoals"]):
                        if (goal.get("numerical_or_TF") == "TF") and (index > TF_index):
                            exist_next_TF = True
                            next_TF_index = index
                            break
                    
                    if exist_next_TF:
                        result["TF_index"] = next_TF_index
                        gpt_message += f"次に、TF目標「{result["subGoals"][next_TF_index]["shortTerm_goal"]}」について、最小単位の仕事の単位であるタスクに分解していきましょう。どのようなタスクに分解できますか？"
                        chat_messages.append(AIMessage(content=gpt_message))

                    else:
                        result["isTerminated"] = True
                        chat_messages.append(AIMessage(content=gpt_message))
                    
                    result["response"] = gpt_message
                    result['session_messages'] = [message_to_dict(m) for m in chat_messages]
                    print(json.dumps(result, ensure_ascii=False))
                    sys.exit(0)

                except Exception as e:
                    error_message = f'OpenAI API Error: {str(e)}, stage 2'
                    print(json.dumps({'error': error_message}), file=sys.stderr)
                    sys.exit(1)

            else:
                chat_messages.append(AIMessage(content=gpt_message))
                result["TF_index"] = TF_index
                result["response"] = gpt_message
                result['session_messages'] = [message_to_dict(m) for m in chat_messages]
                print(json.dumps(result, ensure_ascii=False))
                

        except Exception as e:
            error_message = f'OpenAI API Error: {str(e)}, stage 2'
            print(json.dumps({'error': error_message}), file=sys.stderr)
            sys.exit(1)

        



def initial_system_message_content():
    return """
あなたは、会社の上司の役割を持つアシスタントです。ユーザーが何も知らない前提で、大目標から2つの小目標を生成するプロセスを全面的にリードしてください。
小目標は1カ月間の想定です。
プロセスは以下の手順で行います：
1. 大目標に対して、どのような小目標が考えられるかをユーザーに尋ねる。
2. ユーザーが提示した小目標が不十分(すぐに達成可能または大目標からの関連性が不明)な場合もしくは1つしかない場合、新たに小目標をユーザーに尋ねる。ユーザーが行き詰まっていれば、小目標を提案する。
3. 提示した小目標を踏まえて、ユーザーに決定させる。
すべてのプロセスが終了後、'小目標の設定が完了しました'と出力してください。
    """



def second_system_message_content():
    return """
あなたは、会社の上司の役割を持つアシスタントです。ユーザーが何も知らない前提で、ユーザが小目標からKPIを生成し、数値基準目標かTF(True or False)目標かを判断するプロセスを全面的にリードしてください。
小目標は1カ月間の想定です。
プロセスは以下の手順で行います：
1. 大目標に対して、どのような小目標が考えられるかをユーザーに尋ねる。
2. ユーザーが提示した小目標が不十分(すぐに達成可能または大目標からの関連性が不明)な場合もしくは1つしかない場合、新たに小目標をユーザーに尋ねる。ユーザーが行き詰まっていれば、小目標を提案する。
3. 提示した小目標を踏まえて、ユーザーに決定させる。
すべてのプロセスが終了後、'小目標の設定が完了しました'と出力してください。
    """

def third_system_message_content(short_term_goal_item):
    return f"""
小目標：{short_term_goal_item}

あなたはユーザのAI上司です。
上記の小目標に対して、ユーザがKPIを設定し、小目標を分類する手伝いをしてください。
プロセスは以下の手順で行います：
1. 小目標に対して、考えられるKPIをユーザーに尋ねる。
2. ユーザーが提示したKPIが、達成度を数値で評価可能ならば小目標の分類を"numerical"とし、達成したかしてないかの2状態で評価される目標ならば、小目標の分類を"TF"とする
3. 変数'KPI_indicator'を設定する。
この変数は、小目標の分類が"numerical"の場合、その数値の達成の基準となる数値であり、小目標の分類が"TF"の場合、1となります。
(ex)
〜を5個達成する → 分類："numerical", "KPI_indicator"：5
〜の操作をできるようになる → 分類："TF", "KPI_indicator"：1
〜を10%向上させる → 分類："numerical", "KPI_indicator"：10

出力には小目標,KPI,分類,KPI_indicatorを全て含めてください。
すべてのプロセスが終了後、'KPI設定・目標分類が完了しました'と出力してください。
"""

def forth_system_message_content(short_term_goal_item):
    return f"""
小目標：{short_term_goal_item}

上記の小目標に対して、ユーザが小目標を、最小のタスクに分解する手伝いをしてください。

1. 小目標に対して、ユーザーにタスクを最小限に分解させる。この際、極力ユーザに考えさせる。
2. プロセスが完了すれば、'小目標「{short_term_goal_item}」のタスク分解が完了しました'と出力してください

出力には小目標,KPI,分類,KPI_indicator,分解したタスクを全て含めてください。"""


def extract_json_from_text(text):
    # テキストからJSON部分のみを抽出する
    json_str = re.search(r'\[.*\]', text, re.DOTALL)
    if json_str:
        return json_str.group()
    else:
        return text  # JSON部分が見つからない場合は元のテキストを返す

def convert_to_langchain_messages(messages):
    langchain_messages = []
    for msg in messages:
        role = msg.get('role')
        content = msg.get('content')
        if role == 'system':
            langchain_messages.append(SystemMessage(content=content))
        elif role == 'user':
            langchain_messages.append(HumanMessage(content=content))
        elif role == 'assistant':
            langchain_messages.append(AIMessage(content=content))
        else:
            # デフォルトでHumanMessageとする
            langchain_messages.append(HumanMessage(content=content))
    return langchain_messages

def message_to_dict(message):
    if isinstance(message, SystemMessage):
        role = 'system'
    elif isinstance(message, HumanMessage):
        role = 'user'
    elif isinstance(message, AIMessage):
        role = 'assistant'
    else:
        role = 'user'
    return {'role': role, 'content': message.content}

if __name__ == '__main__':
    main()