from langchain_openai.chat_models import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.schema.runnable import RunnableSequence
import os
from dotenv import load_dotenv

load_dotenv()

# 中間結果を収集するクラス
class OutputCollector:
    def __init__(self):
        self.outputs = []

    def __call__(self, x):
        self.outputs.append(x.content)
        return x

collector = OutputCollector()

llm = ChatOpenAI(
    model_name="gpt-3.5-turbo",
    openai_api_key=os.getenv("OPENAI_API_KEY")
)

# 最初のプロンプト
prompt_1 = PromptTemplate(
    input_variables=["job"],
    template="{job}に一番オススメのプログラミング言語は何?"
)

# 2番目のプロンプト
prompt_2 = PromptTemplate(
    input_variables=["programming_language"],
    template="{programming_language}を学ぶためにやるべきことを3ステップで100文字で教えて。"
)

# チェーンの構築
chain = RunnableSequence(
    prompt_1 | llm | 
    collector |  # 最初の結果を収集
    (lambda x: {"programming_language": x.content}) |
    prompt_2 | llm |
    collector    # 2番目の結果を収集
)

# チェーンの実行
chain.invoke({"job": "データサイエンティスト"})

# 結果の出力
print("1個目の結果：")
print(collector.outputs[0])
print("2個目の結果：")
print(collector.outputs[1])