from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest
from itsdangerous import TimestampSigner, BadSignature, SignatureExpired
import motor.motor_asyncio
import uuid
from pydantic import BaseModel
from typing import List
import os
from dotenv import load_dotenv
from langchain.chat_models import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage, AIMessage, BaseMessage
import uvicorn
import re
import json
import sys
from openai import OpenAI
from motor.motor_asyncio import AsyncIOMotorClient
from bson.objectid import ObjectId

# 環境変数のロード
load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")
mongo_url = os.getenv("MONGOURL")
secret_key = os.getenv("SECRET_KEY", "your_secret_key")  

# FastAPIアプリケーションの作成
app = FastAPI()

# CORSとクッキーの設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# MongoDBセッションミドルウェアの定義
class MongoDBSessionMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, secret_key: str, mongo_url: str, max_age: int = 3600):
        super().__init__(app)
        self.signer = TimestampSigner(secret_key)
        self.max_age = max_age
        self.client = motor.motor_asyncio.AsyncIOMotorClient(mongo_url)
        self.db = self.client['session_db']
        self.collection = self.db['sessions']

    async def dispatch(self, request: StarletteRequest, call_next):
        session_id = request.cookies.get('fastapi_session_id')
        request.state.session = {}

        if session_id:
            try:
                session_id = self.signer.unsign(session_id, max_age=self.max_age).decode()
                session_data = await self.collection.find_one({'_id': session_id})
                if session_data:
                    request.state.session = session_data['data']
            except (BadSignature, SignatureExpired):
                pass

        response = await call_next(request)

        # セッションIDを生成し、セッションデータを保存
        session_id = str(uuid.uuid4())
        signed_session_id = self.signer.sign(session_id).decode()
        await self.collection.update_one({'_id': session_id}, {'$set': {'data': request.state.session}}, upsert=True)
        response.set_cookie('fastapi_session_id', signed_session_id, max_age=self.max_age, httponly=True)

        return response

# カスタムセッションミドルウェアの追加（CORSミドルウェアの後に追加）
app.add_middleware(
    MongoDBSessionMiddleware,
    secret_key=secret_key,
    mongo_url=mongo_url,
    max_age=3600  # セッションの有効期限（秒）
)

# Pydanticモデルの定義
class Message(BaseModel):
    role: str
    content: str

class GPTRequest(BaseModel):
    messages: List[Message]

class ShortTermGoalItem(BaseModel):
    shortTerm_goal: str
    importance: int  # 1=高, 2=中, 3=低
    numerical_or_TF: str  # "numerical" または "TF"
    KPI: str  # 必須フィールド
    KPI_indicator: int  # 必須フィールド

class ShortTermGoal(BaseModel):
    shortTermGoals: list[ShortTermGoalItem]  # ShortTermGoalItemのリストに変更

class TaskItem(BaseModel):
    title: str
    importance: int  # 1=高, 2=中, 3=低

class ShortTermGoalItemCompleted(BaseModel):
    shortTerm_goal: str
    KPI: str
    numerical_or_TF: str
    KPI_indicator: int
    priority: int  # 1=高, 2=中, 3=低
    tasks: list[TaskItem]


def convert_to_langchain_messages(messages):
    langchain_messages = []
    for msg in messages:
        if isinstance(msg, dict):
            role = msg.get('role')
            content = msg.get('content')
        elif isinstance(msg, Message):
            role = msg.role
            content = msg.content
        elif isinstance(msg, BaseMessage):
            # すでにLangChainのメッセージオブジェクトの場合
            langchain_messages.append(msg)
            continue
        else:
            raise ValueError(f"Unsupported message type: {type(msg)}")

        if role == 'system':
            langchain_messages.append(SystemMessage(content=content))
        elif role == 'user':
            langchain_messages.append(HumanMessage(content=content))
        elif role == 'assistant':
            langchain_messages.append(AIMessage(content=content))
        else:
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

def initial_system_message_content():
    return """
あなたは、会社の上司の役割を持つアシスタントです。
このステップでは、ユーザーが何も言語化していない前提で、小目標設定のための現状の理解を促すコーチングを実行してください。
小目標の設定は次のステップで行います。
現状の理解とは、ユーザー自身が今持っているものや目標達成のために何が足りないのかを理解することです。

コーチングでは以下の事柄を順守してください:
・相槌を交える。ではを使わない
・一度に一つの質問を行う
・原因や理由について問わない
・はい・いいえで回答できない具体的かつポジティブな質問をする
・回答を深掘りする
・提案を行わない

以下は現状の理解の一例です：
・時間
・現状目標に対して取り組んでいること
・頼れる人

プロセスは以下の手順で行います：
1. このステップの目的を話す
2. 短い例示を交えながら、現状の理解を促すコーチングを行う。
3. OKであれば現状をまとめる。問題があればその理由を考慮して上記のプロセスに戻る。

すべてのプロセスが終了後、'現状把握が完了しました'と出力して回答を終了してください。
"""

def second_system_message_content():
    return """
あなたは、会社の上司の役割を持つアシスタントです。ユーザーが何も知らない前提で、大目標から2つの小目標を生成するプロセスを全面的にリードしてください。
小目標は1カ月間の想定です。

プロセスは以下の手順で行います：
1. 大目標に対して、どのような小目標が考えられるかをユーザーに過不足なく尋ねる。
2. ユーザーが提示した小目標が不十分な場合、新たに小目標をユーザーに尋ねる。

すべてのプロセスが終了後、'小目標の設定が完了しました'と出力して回答を終了してください。
"""

def third_system_message_content(short_term_goal_item):
    return f"""
小目標：{short_term_goal_item}

あなたはユーザのAI上司です。
上記の小目標に対して、ユーザがKPIを設定し、小目標を分類する手伝いをしてください。

プロセスは以下の手順で行います：
1. 小目標に対して、考えられるKPIをユーザーに尋ねる。
2. 各小目標の重要度をユーザに決定させる（高・中・低）。
   - 高：目標達成に不可欠な目標
   - 中：目標達成に重要だが、必須ではない目標
   - 低：目標達成を補助する目標
3. ユーザーが提示したKPIが、達成度を数値で評価可能ならば小目標の分類を"numerical"とし、達成したかしてないかの2状態で評価される目標ならば、小目標の分類を"TF"とする
4. 変数'KPI_indicator'を設定する。
この変数は、小目標の分類が"numerical"の場合、その数値の達成の基準となる数値であり、小目標の分類が"TF"の場合、1となります。
(ex)
〜を5個達成する → 分類："numerical", "KPI_indicator"：5
〜の操作をできるようになる → 分類："TF", "KPI_indicator"：1
〜を10%向上させる → 分類："numerical", "KPI_indicator"：10

出力には小目標,KPI,重要度,分類numerical_or_TF,KPI_indicatorを全て含めてください。
**1つの小目標について上記の操作が完了するたびに、'KPI設定が完了しました'と出力して回答を終了してください。**
"""

def forth_system_message_content(short_term_goal_item):
    return f"""
小目標：{short_term_goal_item}

上記の小目標に対して、ユーザが小目標を、最小のタスクに分解する手伝いをしてください。
各タスクには重要度（高・中・低）を設定します。

1. 小目標に対して、ユーザーにタスクを最小限に分解させる。この際、極力ユーザに考えさせる。
2. 各タスクの重要度をユーザに決定させる。
   - 高：目標達成に不可欠なタスク
   - 中：目標達成に重要だが、必須ではないタスク
   - 低：目標達成を補助するタスク
3. プロセスが完了すれば、'小目標「{short_term_goal_item}」のタスク分解が完了しました'と出力して回答を終了してください。

出力には小目標,KPI,分類,numerical_or_TF,KPI_indicator,分解したタスクと各タスクの重要度を全て含めてください。"""

# MongoDBの接続設定
client = AsyncIOMotorClient(mongo_url)
db = client['your_database_name']  # あなたのデータベース名に変更してください

# メインのエンドポイント
@app.post("/api/gpt")
async def chat_endpoint(request: Request, data: GPTRequest):
    # セッションデータの取得
    session = request.state.session

    # セッションデータの初期化または取得
    session.setdefault("messages", [])
    session.setdefault("stage", 1)
    session.setdefault("goal_num", 1)
    session.setdefault("sub_goals", [])
    session.setdefault("TF_index", -1)
    session.setdefault("isTerminated", False)

    # ユーザーからの新しいメッセージを取得
    user_messages = data.messages

    # セッション内のメッセージをLangChainのメッセージオブジェクトに変換
    session_messages = convert_to_langchain_messages(session["messages"])
    user_langchain_messages = convert_to_langchain_messages(user_messages)

    # ChatOpenAIのインスタンスを作成
    chat = ChatOpenAI(
        temperature=0,
        model="gpt-4o",  # 必要に応じてモデルを変更
        openai_api_key=openai_api_key
    )
    client = OpenAI(api_key=openai_api_key)

    try:
        # ステージごとの処理
        if session["stage"] == 1:
            # 初回のシステムメッセージを追加
            if not session_messages:
                system_message = SystemMessage(content=initial_system_message_content())
                session_messages.append(system_message)

            # チャットメッセージを更新
            chat_messages = session_messages + user_langchain_messages

            # OpenAI APIを呼び出す
            response = chat(chat_messages)
            gpt_message = response.content

            if '現状把握が完了しました' in gpt_message:
                session['stage'] = 2  # 現状把握から小目標設定へ
                gpt_message += "\n\n次のステップとして、大目標から小目標を考えていきましょう。どのような小目標が考えられますか"

            # 応答をセッションに保存
            session_messages.extend(user_langchain_messages)
            session_messages.append(AIMessage(content=gpt_message))
            session["messages"] = [message_to_dict(m) for m in session_messages]

            # セッションデータを保存
            request.state.session = session

            # レスポンスを返す
            return JSONResponse({"response": gpt_message, "subGoals": session.get("sub_goals", []), "isTerminated": session["isTerminated"]})

        elif session["stage"] == 2:
            # システムメッセージを追加
            chat_messages = session_messages + [
                SystemMessage(content=second_system_message_content())
            ] + user_langchain_messages

            # OpenAI APIを呼び出す
            response = chat(chat_messages)
            gpt_message = response.content

            if '小目標の設定が完了しました' in gpt_message:
                try:
                    completion2 = client.beta.chat.completions.parse(
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
                    
                    # 小目標を保存
                    session["sub_goals"] = [{
                        "shortTerm_goal": item.shortTerm_goal,
                    } for item in completion2.choices[0].message.parsed.shortTermGoals]
                    session['stage'] = 3
                    gpt_message += f"\n次のステップとして、最初の目標である「{session['sub_goals'][0]['shortTerm_goal']}」について、重要度とKPIを設定しましょう。"

                except Exception as e:
                    error_message = f'OpenAI API Error: {str(e)}, stage 2'
                    print(json.dumps({'error': error_message}), file=sys.stderr)
                    sys.exit(1)

            # 応答をセッションに保存
            session_messages.extend(user_langchain_messages)
            session_messages.append(AIMessage(content=gpt_message))
            session["messages"] = [message_to_dict(m) for m in session_messages]

            # セッションデータを保存
            request.state.session = session

            # レスポンスを返す
            return JSONResponse({"response": gpt_message, "subGoals": session.get("sub_goals", []), "isTerminated": session["isTerminated"]})

        elif session["stage"] == 3:
            current_goal_index = session["goal_num"] - 1  # インデックスを計算
            
            # システムメッセージを追加
            chat_messages = session_messages + [
                SystemMessage(content=third_system_message_content(session["sub_goals"][current_goal_index]["shortTerm_goal"]))
            ] + user_langchain_messages

            # OpenAI APIを呼び出す
            response = chat(chat_messages)
            gpt_message = response.content

            if 'KPI設定が完了しました' in gpt_message:
                try:
                    completion2 = client.beta.chat.completions.parse(
                        model="gpt-4o",
                        messages=[
                            {"role": "system", "content": "あなたの仕事は、文章の要約です"},
                            {"role": "user", "content": f"""
{chat_messages}
上記の会話ログから、以下の情報をリスト形式で出力してください：
1. 小目標
2. 重要度(1=高, 2=中, 3=低)
3. KPI（目標の評価指標）
4. 目標の種類（数値で評価可能な場合は"numerical"、達成/未達成の2状態で評価される場合は"TF"）
5. KPI_indicator（数値目標の場合は目標値、TF目標の場合は1）
"""},
                        ],
                        response_format=ShortTermGoalItem,
                    )
                    
                    parsed_data = completion2.choices[0].message.parsed.dict()
                    # 現在のインデックスの小目標を更新
                    session["sub_goals"][current_goal_index].update({
                        "importance": parsed_data["importance"],
                        "KPI": parsed_data["KPI"],
                        "numerical_or_TF": parsed_data["numerical_or_TF"],
                        "KPI_indicator": parsed_data["KPI_indicator"],
                        "current_achievement_num": 0
                    })

                    session["goal_num"] += 1
                    if current_goal_index + 1 >= len(session["sub_goals"]):  # インデックスで比較
                        # すべての小目標のKPI設定が完了
                        session["stage"] = 4
                        for index, goal in enumerate(session["sub_goals"]):
                            if goal.get("numerical_or_TF") == "TF":
                                session["TF_index"] = index
                                gpt_message += f"\n次に、TF目標「{goal['shortTerm_goal']}」について、タスク分解を行いましょう。"
                                break
                    else:
                        # 次の小目標のKPI設定へ
                        next_goal = session["sub_goals"][current_goal_index + 1]["shortTerm_goal"]  # 次のインデックス
                        gpt_message += f"\n次の目標である「{next_goal}」について、重要度とKPIを設定しましょう。"

                except Exception as e:
                    error_message = f'OpenAI API Error: {str(e)}, stage 3'
                    print(json.dumps({'error': error_message}), file=sys.stderr)
                    sys.exit(1)

            # 応答をセッションに保存
            session_messages.extend(user_langchain_messages)
            session_messages.append(AIMessage(content=gpt_message))
            session["messages"] = [message_to_dict(m) for m in session_messages]

            # セッションデータを保存
            request.state.session = session

            # レスポンスを返す
            return JSONResponse({"response": gpt_message, "subGoals": session.get("sub_goals", []), "isTerminated": session["isTerminated"]})

        elif session["stage"] == 4:
            # システムメッセージを追加
            chat_messages = session_messages + [
                SystemMessage(content=forth_system_message_content(session["sub_goals"][session["TF_index"]]["shortTerm_goal"]))
            ] + user_langchain_messages

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
{chat_messages},
{gpt_message}
上記の会話ログから、小目標、KPI、numerical_or_TF、KPI_indicator、tasksをリスト形式で出力してください。
各タスクには title と importance (1=高, 2=中, 3=低) を含めてください。
"""},
                        ],
                        response_format=ShortTermGoalItemCompleted,
                    )

                    # Stage 4でのタスク更新処理
                    parsed_data = completion3.choices[0].message.parsed.dict()
                    current_index = session["TF_index"]
                    session["sub_goals"][current_index].update({
                        "tasks": [
                            {
                                "title": task["title"],
                                "importance": task["importance"],
                                "completed": False
                            }
                            for task in parsed_data["tasks"]
                        ]
                    })

                    # 次のTF目標があるか確認
                    next_tf_found = False
                    for index in range(current_index + 1, len(session["sub_goals"])):
                        if session["sub_goals"][index].get("numerical_or_TF") == "TF":
                            session["TF_index"] = index
                            next_TF_goal = session["sub_goals"][index]["shortTerm_goal"]
                            gpt_message += f"\n次に、TF目標「{next_TF_goal}」について、タスク分解を行いましょう。"
                            next_tf_found = True
                            break
                    
                    if not next_tf_found:
                        session["isTerminated"] = True

                except Exception as e:
                    error_message = f'OpenAI API Error: {str(e)}, stage 4'
                    print(json.dumps({'error': error_message}), file=sys.stderr)
                    sys.exit(1)

            # 応答をセッションに保存
            session_messages.extend(user_langchain_messages)
            session_messages.append(AIMessage(content=gpt_message))
            session["messages"] = [message_to_dict(m) for m in session_messages]

            # セッションデータを保存
            request.state.session = session

            # レスポンスを返す
            return JSONResponse({"response": gpt_message, "subGoals": session.get("sub_goals", []), "isTerminated": session["isTerminated"]})

        elif session["stage"] == 5:
            # ステージ5の処理
            TF_index = session["TF_index"]
            sub_goals = session["sub_goals"]

            if TF_index >= 0 and TF_index < len(sub_goals):
                current_TF_goal = sub_goals[TF_index]["shortTerm_goal"]

                # チャットメッセージを更新（システムメッセージは追加しない）
                chat_messages = session_messages + user_langchain_messages

                # OpenAI APIを呼び出す
                response = chat(chat_messages)
                gpt_message = response.content

                if 'タスク分解が完了しました' in gpt_message:
                    try:
                        completion3 = client.beta.chat.completions.parse(
                            model="gpt-4",
                            messages=[
                                {"role": "system", "content": "あなたの仕事は、文章の要約です"},
                                {"role": "user", "content": f"""
{chat_messages}
上記の会話ログから、小目標、KPI、numerical_or_TF、KPI_indicator、tasksをリスト形式で出力してください。
"""},
                            ],
                            response_format=ShortTermGoalItemCompleted,
                        )

                        session["sub_goals"][TF_index] = completion3.choices[0].message.parsed.dict()

                        # 次のTF目標があるか確認
                        exist_next_TF = False
                        for index in range(TF_index + 1, len(sub_goals)):
                            if sub_goals[index].get("numerical_or_TF") == "TF":
                                session["TF_index"] = index
                                next_TF_goal = sub_goals[index]["shortTerm_goal"]
                                gpt_message += f"\n次に、TF目標「{next_TF_goal}」について、タスク分解を行いましょう。"
                                exist_next_TF = True
                                break
                        if not exist_next_TF:
                            # すべてのTF目標のタスク分解が完了
                            session["isTerminated"] = True

                    except Exception as e:
                        error_message = f'OpenAI API Error: {str(e)}, stage 5'
                        print(json.dumps({'error': error_message}), file=sys.stderr)
                        sys.exit(1)

                # 応答をセッションに保存
                session_messages.extend(user_langchain_messages)
                session_messages.append(AIMessage(content=gpt_message))
                session["messages"] = [message_to_dict(m) for m in session_messages]

                # セッションデータを保存
                request.state.session = session

                # レスポンスを返す
                return JSONResponse({"response": gpt_message, "subGoals": session.get("sub_goals", []), "isTerminated": session["isTerminated"]})

            else:
                return JSONResponse({"error": "TF目標が存在しません"}, status_code=400)

        else:
            # ステージが未定義の場合のエラー処理
            return JSONResponse({"error": "無効なステージです"}, status_code=400)

    except Exception as e:
        import traceback
        traceback_str = ''.join(traceback.format_exception(None, e, e.__traceback__))
        # エラーログをコンソールに出力
        print(traceback_str)
        return JSONResponse({"error": str(e), "traceback": traceback_str}, status_code=500)

async def generate_mentoring_advice(chat_history):
    try:
        prompt = f"""
        以下のメンタリングセッションの履歴を基に、
        ユーザーへの具体的なアドバイスを生成してください：

        メンタリング履歴：
        {chat_history}

        以下の3つの観点から、具体的で実用的なアドバイスを提供してください：
        1. 現状分析：
        - ユーザーの現在の状況
        - 強みと改善点

        2. 目標達成のための具体的なアドバイス：
        - 設定された目標に対する具体的な行動指針
        - 予想される課題と対処方法
        - 進捗管理の方法

        3. モチベーション維持のためのメッセージ：
        - 目標達成による具体的なメリット
        - 励ましの言葉
        """
        
        client = OpenAI(api_key=openai_api_key)
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "あなたは経験豊富なキャリアメンターとして、ユーザーの目標達成を支援します。"},
                {"role": "user", "content": prompt}
            ]
        )
        
        print("OpenAI Response:", response)
        return response.choices[0].message.content
        
    except Exception as e:
        print(f"Error in generate_mentoring_advice: {str(e)}")
        raise

# FastAPIのエンドポイントとして追加
@app.post("/api/generate-advice")
async def generate_advice(request: Request):
    print("アドバイス生成APIが呼び出されました")
    try:
        data = await request.json()
        print("受信したデータ:", data)
        chat_history = data.get('chat_history')
        
        if not chat_history:
            raise HTTPException(status_code=400, detail="チャット履歴が必要です")
            
        advice = await generate_mentoring_advice(chat_history)
        return {"advice": advice}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# サーバーの起動
if __name__ == "__main__":
    uvicorn.run("gpt_chat2:app", host="0.0.0.0", port=8000, reload=True)