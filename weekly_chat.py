from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest
from itsdangerous import TimestampSigner, BadSignature, SignatureExpired
import motor.motor_asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from bson.objectid import ObjectId
import uuid
from pydantic import BaseModel
from typing import List, Optional
import os
from dotenv import load_dotenv
from langchain.chat_models import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage, AIMessage, BaseMessage
import openai
from openai import AsyncOpenAI
import json
import sys
from enum import Enum

# 環境変数のロード
load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")
openai.api_key = openai_api_key  # APIキーを設定
mongo_url = os.getenv("MONGOURL")
secret_key = os.getenv("SECRET_KEY", "your_secret_key")

# OpenAIクライアントの初期化
client = AsyncOpenAI(api_key=openai_api_key)

# FastAPIアプリケーションの作成
app = FastAPI()

# CORSミドルウェアを最初に追加
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
        # コレクション名は初期化時にはセットせず、dispatch時に設定する
        self.collection = None

    async def dispatch(self, request: StarletteRequest, call_next):
        # リクエストから目標番号を取得
        try:
            body = await request.json()
            goal_num = body.get('goal_num', 0)
        except:
            goal_num = 0

        # 目標番号に応じてコレクションを設定
        self.collection = self.db[f'weekly_sessions_{goal_num + 1}']

        session_id = request.cookies.get('weekly_session_id')
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

        if hasattr(request.state, 'session'):
            # セッションIDを生成し、セッションデータを保存
            session_id = str(uuid.uuid4())
            signed_session_id = self.signer.sign(session_id).decode()
            await self.collection.update_one(
                {'_id': session_id}, 
                {'$set': {'data': request.state.session}}, 
                upsert=True
            )
            response.set_cookie(
                'weekly_session_id', 
                signed_session_id, 
                max_age=self.max_age, 
                httponly=True
            )

        return response

# その後に他のミドルウェアを追加
app.add_middleware(
    MongoDBSessionMiddleware,
    secret_key=secret_key,
    mongo_url=mongo_url,
    max_age=3600
)

class WeeklyMeetingStage:
    ACHIEVEMENT_CHECK = 1
    CURRENT_SITUATION = 2
    NEXT_GOAL = 3

class ChatMessage(BaseModel):
    role: str
    content: str

class TaskStatus(str, Enum):
    NOT_STARTED = 'not_started'
    IN_PROGRESS = 'in_progress'
    COMPLETED = 'completed'

class TaskProgress(BaseModel):
    title: str
    completed: bool
    importance: int
    status: TaskStatus = TaskStatus.NOT_STARTED

class NumericalProgress(BaseModel):
    current_achievement_num: int

class TFProgress(BaseModel):
    task_status: List[bool]  # タスクの順序通りの完了状態リスト

# ShortTermGoalProgressを他のモデルより先に定義
class ShortTermGoalProgress(BaseModel):
    shortTerm_goal: str
    KPI: str
    numerical_or_TF: str
    KPI_indicator: Optional[int] = None
    current_achievement_num: Optional[int] = None
    weekly_goal_num: Optional[int] = None  # 週ごとの目標値を追加
    importance: Optional[int] = None
    status: TaskStatus = TaskStatus.NOT_STARTED
    tasks: Optional[List[TaskProgress]] = None

class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    goal_num: int
    shortTermGoal: Optional[ShortTermGoalProgress] = None  # 1つの目標を受け取る

@app.post("/weekly-chat")
async def handle_weekly_meeting(request: Request, data: ChatRequest):
    try:
        session = request.state.session
        current_goal = data.shortTermGoal
        print(f"current_goal: {current_goal}")
        print(f"KPI: {current_goal.KPI}")

        if session.get("messages"):        # メッセージの処理
            user_messages = [{"role": msg.role, "content": msg.content} for msg in data.messages]
            session_messages = convert_to_langchain_messages(session["messages"])
            user_langchain_messages = convert_to_langchain_messages(user_messages)

            chat_messages = session_messages + user_langchain_messages
        
        # セッションの初期化
        else:
            session.setdefault("messages", [])
            session.setdefault("stage", WeeklyMeetingStage.ACHIEVEMENT_CHECK)
            session.setdefault("goal_num", 0)
            session.setdefault("shortTermGoal", {})  # 配列ではなく辞書として初期化
            session.setdefault("isTerminated", False)
            session.setdefault("is_confirmed", False)
            
            # 最初のシステムメッセージを設定
            system_message = weekly_first_system_message_content(current_goal)
            chat_messages = [SystemMessage(content=system_message)]
            session_messages = chat_messages  # セッションにシステムメッセージを保存
            session["messages"] = [message_to_dict(m) for m in session_messages]  # 辞書形式で保存
            user_langchain_messages = []
    
        chat = ChatOpenAI(temperature=0)
        
        response = chat(chat_messages)
        gpt_message = response.content
        session["is_confirmed"] = False # ユーザーの確認を受けていない場合はFalse   

        if "達成率の確認が完了しました" in gpt_message:
            session["is_confirmed"] = True
            session["stage"] = WeeklyMeetingStage.CURRENT_SITUATION
            gpt_message += "次に、今週の状況について伺います。今週の予定や割り当て可能な時間について教えてください"
            
            # メッセージの追加方法を修正
            session_messages.extend(user_langchain_messages)
            session_messages.append(AIMessage(content=gpt_message))
            session_messages.append(SystemMessage(content=weekly_third_system_message_content()))
            session["messages"] = [message_to_dict(m) for m in session_messages]

            if current_goal.numerical_or_TF == "TF":
                completion = await client.beta.chat.completions.parse(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": "あなたの仕事は、ユーザの小目標の更新です"},
                        {"role": "user", "content": f"""
    現在の小目標の状況：{current_goal}
    会話ログ：{chat_messages}

    上記の会話履歴から、小目標とそのタスクについて、status：現在の状況を更新してください。その他の項目は変更しないでください。
    """},
                    ],
                    response_format=ShortTermGoalProgress,
                )

            else: # numericalの場合 
                completion = await client.beta.chat.completions.parse(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": "あなたの仕事は、ユーザの小目標の更新です"},
                        {"role": "user", "content": f"""
現在の小目標の状況：{current_goal}
会話ログ：{chat_messages}

会話の流れから、current_achievement_num：現在の達成値、およびstatus：現在の状況を更新してください。その他の項目は変更しないでください。
    """},
                    ],
                    response_format=ShortTermGoalProgress,
                )
            
            parsed_data = completion.choices[0].message.parsed.dict()
            print(f"parsed_data: {parsed_data}")
            # 現在のインデックスの小目標を更新
            session["shortTermGoal"] = {
                "shortTerm_goal": parsed_data["shortTerm_goal"],
                "KPI": parsed_data["KPI"],
                "numerical_or_TF": parsed_data["numerical_or_TF"],
                "KPI_indicator": parsed_data["KPI_indicator"],
                "current_achievement_num": parsed_data["current_achievement_num"],
                "weekly_goal_num": parsed_data["weekly_goal_num"],
                "importance": parsed_data["importance"],
                "status": parsed_data["status"],
                "tasks": parsed_data["tasks"]
            }

        if "現状の理解が完了しました" in gpt_message:
            session["stage"] = WeeklyMeetingStage.NEXT_GOAL
            if current_goal.numerical_or_TF == "TF":
                gpt_message += "次に、今週取り組むアクションを決めます。どのアクションに取り組みましょうか"
                
                # メッセージの追加方法を修正
                session_messages.extend(user_langchain_messages)
                session_messages.append(AIMessage(content=gpt_message))
                session_messages.append(SystemMessage(content=weekly_forth_system_message_content(current_goal)))
            else:
                gpt_message += "次に、今週の目標数値を決めます。今週の目標数値を考えましょう。"
                
                # メッセージの追加方法を修正
                session_messages.extend(user_langchain_messages)
                session_messages.append(AIMessage(content=gpt_message))
                session_messages.append(SystemMessage(content=weekly_fifth_system_message_content(current_goal)))
            
            session["messages"] = [message_to_dict(m) for m in session_messages]

        if "週次コーチングが完了しました" in gpt_message:
            if current_goal.numerical_or_TF == "TF":
                completion = await client.beta.chat.completions.parse(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": "あなたの仕事は、ユーザの小目標の更新です"},
                        {"role": "user", "content": f"""
    現在の小目標の状況：{current_goal}
    会話ログ：{chat_messages}

    上記の会話履歴から、小目標とそのタスクについて、status：着手状況を更新してください。その他の項目は変更しないでください。
    """},
                    ],
                    response_format=ShortTermGoalProgress,
                )

            else: # numericalの場合 
                completion = await client.beta.chat.completions.parse(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": "あなたの仕事は、ユーザの小目標の更新です"},
                        {"role": "user", "content": f"""
現在の小目標の状況：{current_goal}
会話ログ：{chat_messages}

会話の流れから、weekly_goal_num：今週の目標値、およびstatus：現在の状況を更新してください。その他の項目は変更しないでください。
    """},
                    ],
                    response_format=ShortTermGoalProgress,
                )
            
            parsed_data = completion.choices[0].message.parsed.dict()
            print(f"parsed_data: {parsed_data}")
            # 現在のインデックスの小目標を更新
            session["shortTermGoal"] = {
                "shortTerm_goal": parsed_data["shortTerm_goal"],
                "KPI": parsed_data["KPI"],
                "numerical_or_TF": parsed_data["numerical_or_TF"],
                "KPI_indicator": parsed_data["KPI_indicator"],
                "current_achievement_num": parsed_data["current_achievement_num"],
                "weekly_goal_num": parsed_data["weekly_goal_num"],
                "importance": parsed_data["importance"],
                "status": parsed_data["status"],
                "tasks": parsed_data["tasks"]
            }

            session["isTerminated"] = True # １つの小目標のコーチングが完了したら、終了フラグを立てる
            session["goal_num"] += 1 # 小目標のインデックスを更新

        else:
            session_messages.extend(user_langchain_messages)
            session_messages.append(AIMessage(content=gpt_message))
            session["messages"] = [message_to_dict(m) for m in session_messages]

        # セッションデータを保存
        request.state.session = session

        return {
            "response": gpt_message,
            "stage": session["stage"],
            "goal_num": session["goal_num"],
            "isTerminated": session["isTerminated"],
            "shortTermGoal": session["shortTermGoal"],
            "is_confirmed": session["is_confirmed"]
        }

    except Exception as e:
        error_message = f'Error in weekly meeting: {str(e)}'
        print(json.dumps({'error': error_message}), file=sys.stderr)
        return JSONResponse({"error": error_message}, status_code=500)

def weekly_first_system_message_content(shortTerm_goal):
    if shortTerm_goal.numerical_or_TF=="TF":
        return f"""
小目標： {shortTerm_goal.shortTerm_goal}

目標アクション：
    {shortTerm_goal.tasks}
あなたは、会社の上司の役割を持つ対話型アシスタントです。
上記の小目標と目標アクションに対して、ユーザが現状の達成度合いを振り返るための補佐をしてください。
コーチングでは以下の事柄を順守してください:
・目標アクションを細分化しない
・肯定的な相槌を交える。「では」を使わない
・一度に一つだけ質問を行う
・原因・理由・状態・次に取り組むこと・サポートについて問わない
以下はコーチングでの必須質問です：
・仮に何を行えば達成できたか
プロセスは以下の手順で行います：
1. このステップの目的を話す
2. 各アクションを達成したか否かを決める
3. 短い例示を交えながら、目標アクションのコーチングを行う。ユーザーが十分な理解が得られるまで繰り返す
4. OKであれば現状と解決策をまとめユーザーに確認し、問題があればその理由を考慮して上記のプロセスに戻る。
すべてのプロセスが終了後、'達成率の確認が完了しました'と出力してください。"""
    
    else:
        return f"""
小目標： {shortTerm_goal.shortTerm_goal}
KPI: {shortTerm_goal.KPI}
目標数値: {shortTerm_goal.KPI_indicator}
あなたは、対話型の会社の上司の役割を持つアシスタントです。
上記の小目標と目標アクションに対して、ユーザが現状の達成度合いを振り返るための補佐をしてください。
コーチングでは以下の事柄を順守してください:
・目標数値を言い換える
・プロセスを公開しない
・肯定的な相槌を交える。ではを使わない
・一度に一つだけ質問を行う
・原因や理由・現状・次に取り組むことについて問わない
以下はコーチングの質問例です：
・仮に何を行えば達成できたか
プロセスは以下の手順で行います：
1. このステップの目的を話す
2. 進捗を尋ねた後、目標数値に対して、達成したか否かを確認する
3. 短い例示を交えながら、目標数値に対して、どれだけ達成したかを**具体的な数値で**決定するコーチングを行う。ユーザーが十分な理解が得られるまで繰り返す
4. OKであれば現状と解決策をまとめユーザーに確認し、問題があればその理由を考慮して上記のプロセスに戻る。
すべてのプロセスが終了後、'達成率の確認が完了しました'と出力してください。"""

def weekly_third_system_message_content():
    return f"""
あなたは、会社の上司の役割を持つアシスタントです。
次に、ユーザーが何も言語化していない前提で、今週実行するアクション決めのための現状の理解を促すコーチングを実行してください。
現状の理解とは、今週特有の用事や事情などを自覚することです。
コーチングでは以下の事柄を順守してください:
・相槌を交える。ではを使わない
・一度に一つの質問を行う
・原因や理由について問わない
・はい・いいえで回答できない具体的かつポジティブな質問をする
・回答を深掘りする
・アクション決めを行わない
以下は現状の理解を促すコーチングの一例です：
・時間
・体調
プロセスは以下の手順で行います：
1. 話題が変わったことと、このステップの目的を話す
2. 短い例示を交えながら、現状の理解を促すコーチングを行う。ユーザーが十分な理解が得られるまで繰り返す
3. OKであれば現状をまとめた後に終了し、今週全体で使える時間を出力したあと、問題があればその理由を考慮して上記のプロセスに戻る。
すべてのプロセスが終了後、'現状の理解が完了しました'と出力してください。"""

def weekly_forth_system_message_content(shortTerm_goal):
    return f"""
小目標： {shortTerm_goal.shortTerm_goal}
未完了アクション：{shortTerm_goal.tasks}
あなたは、会社の上司の役割を持つアシスタントです。
次に、上記の小目標で、今週実行するアクションを決める補佐をしてください。
コーチングでは以下の事柄を順守してください:
・相槌を交える。ではを使わない
・一度に一つの質問を行う
・原因や理由について問わない
・アクションを細分化しない
プロセスは以下の手順で行います：
1. 短い例示を交えながら、次のアクション決めのコーチングを行う。ユーザーが十分な理解が得られるまで繰り返す
2. OKであれば現状をまとめた後に終了し、問題があればその理由を考慮して上記のプロセスに戻る。
すべてのプロセスが終了後、'週次コーチングが完了しました'と出力してください。"""
def weekly_fifth_system_message_content(shortTerm_goal):
    return f"""
小目標： {shortTerm_goal.shortTerm_goal}
KPI: {shortTerm_goal.KPI}
目標数値: {shortTerm_goal.KPI_indicator}
進捗: {shortTerm_goal.current_achievement_num}
あなたは、会社の上司の役割を持つアシスタントです。
次に、上記の小目標に対して、今週からの目標数値を決める補佐をしてください。
コーチングでは以下の事柄を順守してください:
・相槌を交える。ではを使わない
・一度に一つの質問を行う
・原因や理由・手段について問わない
プロセスは以下の手順で行います：
1. 短い例示を交えながら、目標数値決めのコーチングを行う。ユーザーが十分な理解が得られるまで繰り返す
2 OKであれば現状をまとめた後に終了し、問題があればその理由を考慮して上記のプロセスに戻る。
すべてのプロセスが終了後、'週次コーチングが完了しました'と出力してください。"""

def convert_to_langchain_messages(messages: List[dict]) -> List[BaseMessage]:
    """
    通常のメッセージ形式からLangChainのメッセージ形式に変換する
    """
    langchain_messages = []
    for message in messages:
        if message["role"] == "system":
            langchain_messages.append(SystemMessage(content=message["content"]))
        elif message["role"] == "user":
            langchain_messages.append(HumanMessage(content=message["content"]))
        elif message["role"] == "assistant":
            langchain_messages.append(AIMessage(content=message["content"]))
    return langchain_messages

def message_to_dict(message: BaseMessage) -> dict:
    """
    LangChainのメッセージ形式を通常のdict形式に変換する
    """
    if isinstance(message, SystemMessage):
        return {"role": "system", "content": message.content}
    elif isinstance(message, HumanMessage):
        return {"role": "user", "content": message.content}
    elif isinstance(message, AIMessage):
        return {"role": "assistant", "content": message.content}
    else:
        raise ValueError(f"Unsupported message type: {type(message)}")

async def extract_progress_from_response(gpt_message: str, current_goal: dict) -> dict:
    """GPTの応答から進捗データを抽出"""
    try:
        if current_goal["numerical_or_TF"] == "TF":
            completion = client.beta.chat.completions.parse(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "あなたの仕事は、文章の要約です"},
                    {"role": "user", "content": f"""
{gpt_message}
上記の会話から、各タスクの完了状態をtrue/falseのリストとして抽出してください。
タスクの順序は以下の通りです：
{[task["title"] for task in current_goal["tasks"]]}
"""}
                ],
                response_format=TFProgress
            )
            
            # タスクの完了状態を更新用のデータ形式に変換
            progress_data = {
                "numerical_or_TF": "TF",
                "tasks": [
                    {
                        "title": task["title"],
                        "completed": status,
                        "importance": task["importance"]
                    }
                    for task, status in zip(current_goal["tasks"], completion.choices[0].message.parsed.task_status)
                ]
            }
        else:
            completion = client.beta.chat.completions.parse(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "あなたの仕事は、文章の要約です"},
                    {"role": "user", "content": f"""
{gpt_message}
上記の会話から、達成した数値を抽出してください。
"""}
                ],
                response_format=NumericalProgress
            )
            
            progress_data = {
                "numerical_or_TF": "numerical",
                "current_achievement_num": completion.choices[0].message.parsed.current_achievement_num
            }

        return progress_data

    except Exception as e:
        print(f"Error extracting progress: {str(e)}")
        return None

async def update_progress(user_id: str, goal_index: int, progress_data: dict):
    """ユーザーの進捗データを更新"""
    client = AsyncIOMotorClient(mongo_url)
    db = client['your_database_name']
    users_collection = db['users']

    try:
        if progress_data["numerical_or_TF"] == "TF":
            # TF目標の場合、完了したタスクを更新
            update_query = {
                f"shortTerm_goals.{goal_index}.tasks.$[task].completed": True
            }
            array_filters = [{"task.title": {"$in": progress_data.get("completed_tasks", [])}}]
            
            await users_collection.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": update_query},
                array_filters=array_filters
            )
        else:
            # numerical目標の場合、達成数を更新
            update_query = {
                f"shortTerm_goals.{goal_index}.current_achievement_num": progress_data.get("current_achievement_num", 0)
            }
            
            await users_collection.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": update_query}
            )

        return True
    except Exception as e:
        print(f"Error updating progress: {str(e)}")
        return False

async def generate_response(messages):
    try:
        response = await client.chat.completions.create(
            model="gpt-4",
            messages=messages
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error generating response: {str(e)}")
        raise

@app.post("/generate-advice")
async def generate_advice(request: Request):
    try:
        data = await request.json()
        print("Received data:", data)  # リクエストデータの確認
        chat_history = data.get("messages", [])
        goal = data.get("goal", {})

        advice_prompt = f"""
あなたは優秀なビジネスコーチです。
以下の会話履歴を分析し、次週に向けた具体的なアドバイスを提供してください：

目標：{goal.get('shortTerm_goal')}
KPI：{goal.get('KPI')}

アドバイスは以下の点を含めてください：
1. 今週の取り組みの良かった点
2. 改善できる点
3. 次週に向けた具体的な行動提案
4. モチベーション維持のためのヒント

200文字程度で簡潔にまとめてください。
"""
        print("Generated prompt:", advice_prompt)  # プロンプトの確認
        
        # アドバイス生成用のメッセージを作成
        messages = [
            {"role": "system", "content": "あなたは経験豊富なビジネスコーチです。"},
            *chat_history,  # 会話履歴
            {"role": "user", "content": advice_prompt}
        ]

        print("Sending messages to OpenAI:", messages)  # OpenAIに送信するメッセージの確認

        # OpenAIのAPIを呼び出し
        response = await client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=messages,
            temperature=0.7,
            max_tokens=500
        )

        advice = response.choices[0].message.content
        print("Generated advice:", advice)  # 生成されたアドバイスの確認

        return {"advice": advice}

    except Exception as e:
        logger.error(f"Error generating advice: {str(e)}")
        print(f"Full error details: {str(e)}")  # 詳細なエラー情報の出力
        raise HTTPException(status_code=500, detail=str(e))

# サーバーの起動
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "weekly_chat:app",
        host="0.0.0.0",
        port=8001,  # ポートを明示的に指定
        reload=True
    )

# uvicorn weekly_chat:app --port 8001 --reload