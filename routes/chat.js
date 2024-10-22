const express = require("express");
const router = express.Router();
const OpenAI = require("openai");
const session = require("express-session");
require("dotenv").config();

// express-sessionのミドルウェアをセットアップ
router.use(
  session({
    secret: "your_secret_key", // セッションを暗号化するためのキー
    resave: false,
    saveUninitialized: true,
  })
);

// OpenAIクライアントのインスタンスを作成
const client = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,
});

// 初回のSystemMessage（GPTの役割を説明する）
const initialSystemMessage = {
  role: "system",
  content: `
    あなたは、会社の上司の役割を持つアシスタントです。ユーザーが何も知らない前提で、大目標から2,3つの小目標を生成するプロセスを全面的にリードしてください。
    小目標は1カ月間の想定です。
    プロセスは以下の手順で行います：
    1. 大目標に対して、どのような小目標が考えられるかをユーザーに尋ねる。
    2. ユーザーが提示した小目標が不十分(すぐに達成可能または大目標からの関連性が不明)な場合、新たに小目標を提案する。
    3. 提示した小目標を踏まえて、ユーザーに決定させる。
    4. 選ばれた小目標にそれぞれについて、具体的なKPI（目標値）を決める。
    5. ユーザーに設定した小目標とKPIを確認し、OKかどうかを尋ねる。
    6. OKであれば終了し、問題があればその理由を考慮してKPI設定に戻る。
    すべてのプロセスが終了後、'目標設定が完了しました'と出力してください。
  `,
};

// タスク分割とKPI生成のリクエスト
const generateSubGoalsMessage = {
  role: "system",
  content: `
    次に、設定された小目標とKPIの内容をまとめてください。
    必要のない追加情報は付け加えないでください。
    以下のフォーマットで出力してください：
    [
      { "subgoal": "タスクの割り当て", "KPI": "タスク分担を1週間以内に完了させる" },
      { "subgoal": "進捗確認", "KPI": "進捗報告を週に2回行う" }
    ]
  `,
};

router.post("/", async (req, res) => {
  const { messages } = req.body; // フロントエンドからのメッセージを受け取る

  // セッション内にメッセージ履歴がなければ初期化
  if (!req.session.messages) {
    req.session.messages = [initialSystemMessage];
  }

  const chatMessages =
    messages.length === 0
      ? req.session.messages
      : [...req.session.messages, ...messages];

  try {
    // GPT-3.5のAPIを使用して、まずユーザーの入力に応じた応答を取得
    const response = await client.chat.completions.create({
      model: "gpt-3.5-turbo",
      messages: chatMessages,
      max_tokens: 400,
    });

    const gptMessage = response.choices[0].message.content;

    // セッション内のメッセージ履歴に追加
    req.session.messages.push({ role: "assistant", content: gptMessage });

    // 「目標設定が完了しました」というメッセージが含まれている場合、新たにタスク分割リクエストを送信
    if (gptMessage.includes("目標設定が完了しました")) {
      req.session.messages.push(generateSubGoalsMessage); // セッションにタスク分割のプロンプトを追加

      const subGoalResponse = await client.chat.completions.create({
        model: "gpt-3.5-turbo",
        messages: req.session.messages, // セッション内のメッセージを引き継ぐ
        max_tokens: 400,
      });

      const generatedSubGoals = JSON.parse(
        subGoalResponse.choices[0].message.content
      );
      console.log(generatedSubGoals);

      // セッションを破棄
      req.session.destroy((err) => {
        if (err) {
          console.error("セッションの破棄中にエラーが発生しました:", err);
        } else {
          console.log("会話終了時にセッションを破棄しました");
        }
      });

      // gptMessageとgeneratedSubGoalsをフロントエンドに送信
      return res.json({ response: gptMessage, subGoals: generatedSubGoals });
    }

    // 通常の応答を返す
    res.json({ response: gptMessage });
  } catch (error) {
    console.error("OpenAIとの通信中にエラーが発生しました:", error.message);
    res
      .status(500)
      .json({ error: "OpenAIとの通信中にエラーが発生しました。" });
  }
});

module.exports = router;