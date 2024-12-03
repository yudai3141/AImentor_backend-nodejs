from typing import Annotated
from typing_extensions import TypedDict
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, BaseMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import START, END, StateGraph
from langgraph.graph.message import add_messages

llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash",
    temperature=0,
    max_tokens=None,
    timeout=None,
    max_retries=2,
    api_key="~",
    # other params...
)


class State(TypedDict):
    messages: Annotated[list, add_messages]


def call_model_CurrentSituation(state: State):
    system_prompt = {
        """
        大目標：バックエンドエンジニアになる

        あなたは、会社の上司の役割を持つアシスタントです。
        このステップでは、ユーザーが何も言語化していない前提で、小目標設定のための現状の理解を促すコーチングを実行してください。
        現状の理解とは、ユーザー自身が今持っているものや目標達成のために何が足りないのかを理解することです。"
        コーチングでは以下の事柄を順守してください:
            ・相槌を交える。ではを使わない
            ・一度に一つの質問を行う
            ・原因や理由について問わない
            ・はい・いいえで回答できない具体的かつポジティブな質問をする
            ・回答を深掘りする
        以下は現状の理解を促すコーチングの一例です：
            ・時間
            ・現状目標に対して取り組んでいること
            ・頼れる人
        プロセスは以下の手順で行います：
            1. 短い例示を交えながら、現状の理解を促すコーチングを行う。ユーザーが十分な理解が得られるまで繰り返す
            2. OKであれば現状をまとめた後に終了し、問題があればその理由を考慮して上記のプロセスに戻る。
            すべてのプロセスが終了後、'コーチングが完了しました'と出力してください。
        """
    }

    messages = [SystemMessage(content=system_prompt)] + state["messages"]
    response = llm.invoke(messages)
    return {"messages": response}


def main():
    # phase0();
    workflow = StateGraph(State)

    workflow.add_node("CurrentSituation", call_model_CurrentSituation)
    workflow.add_edge(START, "CurrentSituation")
    workflow.add_edge("CurrentSituation", END)

    memory = MemorySaver()
    app = workflow.compile(checkpointer=memory)

    def stream_graph_updates(user_input: str):
        config = {"configurable": {"thread_id": "1"}}
        result = app.invoke(
            {"messages": [HumanMessage(content=user_input)]},
            config=config,
        )
        print("AI: ", result["messages"][-1].content)
        # events = app.stream(
        #     {"messages": [("user", user_input)]},
        #     config=config,
        #     stream_mode="values",
        # )
        # for event in events:
        #     print(event["messages"][-1].content)

    result = app.invoke(
        {"messages": [HumanMessage(content="")]},
        config={"configurable": {"thread_id": "1"}},
    )
    print("AI: ", result["messages"][-1].content)

    while True:
        try:
            user_input = input("User: ")
            if user_input.lower() in ["quit", "exit", "q"]:
                print("Goodbye!")
                break

            stream_graph_updates(user_input)
        except:
            # fallback if input() is not available
            user_input = "What do you know about LangGraph?"
            print("User: " + user_input)
            stream_graph_updates(user_input)
            break


if __name__ == "__main__":
    main()