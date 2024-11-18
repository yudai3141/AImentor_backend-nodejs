const express = require("express");
const router = express.Router();
const session = require("express-session");
const MongoStore = require("connect-mongo");
const mongoose = require("mongoose");
const { spawn } = require('child_process');
const path = require('path');
require("dotenv").config();

// express-sessionのミドルウェアをセットアップ
router.use(
  session({
    store: MongoStore.create({
      mongoUrl: process.env.MONGOURL, // .envファイルからURLを取得
    }),
    secret: "your_secret_key", // セッションを暗号化するためのキー
    resave: true,
    saveUninitialized: true,
  })
);

router.post("/", async (req, res) => {
  const { messages } = req.body; // フロントエンドからのメッセージを受け取る

  // セッション内にメッセージ履歴がなければ初期化
  if (!req.session.messages) {
    req.session.messages = []; // 初期化（Python側で初期メッセージを設定）
  }

  // セッション内のstageやgoal_numが存在しなければ初期化
  if (req.session.stage === undefined) req.session.stage = 1;
  if (req.session.goal_num === undefined) req.session.goal_num = 1;
  if (req.session.sub_goals === undefined) req.session.sub_goals=[];
  if (req.session.TF_index === undefined) req.session.TF_index=-1;

  try {
    // Pythonスクリプトを呼び出してGPTの応答を取得
    console.log(req.session.sub_goals)
    console.log(req.session.messages)
    const gptResponse = await callPythonGPT(messages, req.session.messages, req.session.stage, req.session.goal_num, req.session.sub_goals, req.session.TF_index);

    const gptMessage = gptResponse.response;
    const generatedSubGoals = gptResponse.subGoals;

    if (gptResponse.stage !== undefined) {
      req.session.stage = gptResponse.stage;
    }
    if (gptResponse.goal_num !== undefined) {
      req.session.goal_num = gptResponse.goal_num;
    }
    if (gptResponse.TF_index !== undefined) {
      req.session.TF_index = gptResponse.TF_index;
    }
    if (gptResponse.subGoals !== undefined) {
      req.session.sub_goals = gptResponse.subGoals;
    }

    if (gptResponse.isTerminated) {
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
    console.error("Pythonスクリプトとの通信中にエラーが発生しました:", error.message);
    res
      .status(500)
      .json({ error: "Pythonスクリプトとの通信中にエラーが発生しました。" });
  }
});

async function callPythonGPT(messages, sessionMessages, stage, goalNum, subGoals, TF_index) {
  return new Promise((resolve, reject) => {
    const scriptPath = path.join(__dirname, '../gpt_chat.py');
    const pythonProcess = spawn('python', [scriptPath]);

    let stdoutData = '';
    let stderrData = '';

    pythonProcess.stdout.on('data', (data) => {
      stdoutData += data.toString();
    });

    pythonProcess.stderr.on('data', (data) => {
      stderrData += data.toString();
    });

    pythonProcess.on('close', (code) => {
      if (code !== 0) {
        reject(new Error(`Pythonスクリプトがコード${code}で終了しました: ${stderrData}`));
      } else {
        try {
          const result = JSON.parse(stdoutData);
          resolve(result);
        } catch (e) {
          reject(new Error(`Pythonスクリプトの出力をパースできませんでした: ${e.message}`));
        }
      }
    });

    // メッセージとセッションメッセージをPythonスクリプトの標準入力に渡す
    const input = JSON.stringify({ messages, session_messages: sessionMessages, stage, goal_num: goalNum, subGoals, TF_index});
    pythonProcess.stdin.write(input);
    pythonProcess.stdin.end();
  });
}

module.exports = router;