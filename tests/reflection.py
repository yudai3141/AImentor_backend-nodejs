import sys
import os
from dotenv import load_dotenv
from langchain.chat_models import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage, AIMessage

def main():
    # 環境変数をロード
    load_dotenv()
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        print('Error: OPENAI_API_KEY is not set.', file=sys.stderr)
        sys.exit(1)

    # ChatOpenAIインスタンスの作成
    chat = ChatOpenAI(
        temperature=0.5,
        model="gpt-4o",  # モデルを必要に応じて変更
        openai_api_key=openai_api_key
    )

    # 初期のシステムメッセージ
    system_message = SystemMessage(content="あなたは親しみやすいアシスタントです。ユーザーの質問に対して丁寧に答えてください。")

    # メッセージ履歴の初期化
    chat_messages = [system_message]

    while True:
        # ユーザーからの入力を受け取る
        user_input = input("ユーザー: ")

        # 終了コマンド
        if user_input.lower() in ["exit", "quit"]:
            print("対話を終了します。")
            break

        # ユーザーのメッセージを追加
        user_message = HumanMessage(content=user_input)
        chat_messages.append(user_message)

        # LLMにメッセージ履歴を渡してレスポンスを取得
        response = chat(chat_messages)
        assistant_message = AIMessage(content=response.content)

        # アシスタントのレスポンスを表示
        print(f"アシスタント: {assistant_message.content}")

        # メッセージ履歴に追加
        chat_messages.append(assistant_message)

if __name__ == "__main__":
    main()