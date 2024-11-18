from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.sessions import SessionMiddleware
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import os
from dotenv import load_dotenv
from langchain.chat_models import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage, AIMessage
import uvicorn

# FastAPIアプリケーションの作成
app = FastAPI()

# セッションミドルウェアの追加
app.add_middleware(SessionMiddleware, secret_key="your_secret_key")

# CORSとクッキーの設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # クライアントのURLに合わせて変更
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydanticモデルの定義
class Message(BaseModel):
    role: str
    content: str

class GPTRequest(BaseModel):
    messages: List[Message]

# 補助関数の定義
def convert_to_langchain_messages(messages):
    langchain_messages = []
    for msg in messages:
        role = msg['role']
        content = msg['content']
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
あなたは、会社の上司の役割を持つアシスタントです。ユーザーが何も知らない前提で、大目標から2つの小目標を生成するプロセスを全面的にリードしてください。
小目標は1カ月間の想定です。
プロセスは以下の手順で行います：
1. 大目標に対して、どのような小目標が考えられるかをユーザーに尋ねる。
2. ユーザーが提示した小目標が不十分(すぐに達成可能または大目標からの関連性が不明)な場合もしくは1つしかない場合、新たに小目標をユーザーに尋ねる。ユーザーが行き詰まっていれば、小目標を提案する。
3. 提示した小目標を踏まえて、ユーザーに決定させる。
すべてのプロセスが終了後、'小目標の設定が完了しました'と出力して回答を終了してください。
    """

# メインのエンドポイント
@app.post("/api/gpt")
async def chat_endpoint(request: Request, data: GPTRequest):
    session = request.session

    # セッションデータの初期化または取得
    session.setdefault("messages", [])
    session.setdefault("stage", 1)
    session.setdefault("goal_num", 1)
    session.setdefault("sub_goals", [])
    session.setdefault("TF_index", -1)

    # ユーザーからの新しいメッセージを取得
    user_messages = data.messages

    # セッション内のメッセージをLangChainのメッセージオブジェクトに変換
    session_messages = convert_to_langchain_messages(session["messages"])
    user_langchain_messages = convert_to_langchain_messages([msg.dict() for msg in user_messages])

    # OpenAI APIキーのロード
    load_dotenv()
    openai_api_key = os.getenv("OPENAI_API_KEY")

    # ChatOpenAIのインスタンスを作成
    chat = ChatOpenAI(
        temperature=0,
        model="gpt-4",  # 必要に応じてモデルを変更
        openai_api_key=openai_api_key
    )

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

        # 応答をセッションに保存
        session_messages.extend(user_langchain_messages)
        session_messages.append(AIMessage(content=gpt_message))
        session["messages"] = [message_to_dict(m) for m in session_messages]

        # 必要に応じてステージや他の状態を更新
        if '小目標の設定が完了しました' in gpt_message:
            session["stage"] = 2
            # 他の状態も更新

        # レスポンスを返す
        return JSONResponse({"response": gpt_message})

    # 他のステージも同様に実装
    # ステージが未定義の場合のエラー処理
    return JSONResponse({"error": "無効なステージです"}, status_code=400)

# サーバーの起動
if __name__ == "__main__":
    uvicorn.run("gpt_chat2:app", host="0.0.0.0", port=8000, reload=True)