const express = require("express");
const router = express.Router();
const axios = require('axios');
const { wrapper } = require('axios-cookiejar-support');
const tough = require('tough-cookie');
const mongoose = require('mongoose');
const { API_ENDPOINTS } = require('../config/constants');

// axiosインスタンスを作成し、クッキージャーを設定
const cookieJar = new tough.CookieJar();
const client = wrapper(axios.create({ jar: cookieJar }));

router.post("/", async (req, res) => {
  console.log("req.body:", req.body);
  const userId = req.body.user_id;
  console.log("userId:", userId);
  try {
    // FastAPIサーバーにリクエストを転送
    const response = await client.post(
      `${API_ENDPOINTS.FASTAPI}/api/gpt/api/gpt/${req.body.user_id}`,
      req.body,
      {
        headers: {
          ...req.headers,
          host: `${API_ENDPOINTS.FASTAPI}`,
        },
        withCredentials: true,
      }
    );

    // クッキーをクライアントに設定
    const setCookieHeader = response.headers['set-cookie'];
    if (setCookieHeader) {
        if (Array.isArray(setCookieHeader)) {
          setCookieHeader.forEach((cookie) => {
            res.append('Set-Cookie', cookie);
          });
        } else {
          res.append('Set-Cookie', setCookieHeader);
        }
      }

    res.status(response.status).json(response.data);

    // メンタリングが終了した場合、セッションをクリア
    if (response.data.isTerminated) {
      await mongoose.connection
        .useDb('session_db')
        .collection(`sessions_${userId}`)
        .deleteMany({});
    }
  } catch (error) {
    console.error("FastAPIサーバーとの通信中にエラーが発生しました:", error.message);
    console.error("エラー詳細:", error);
  
    if (error.response) {
      console.error("エラーレスポンスデータ:", error.response.data);
      res.status(error.response.status).json(error.response.data);
    } else {
      res.status(500).json({ error: "FastAPIサーバーとの通信中にエラーが発生しました。" });
    }
  }
});

// アドバイス生成エンドポイント
router.post("/generate-advice", async (req, res) => {
  try {
    console.log("Received request body:", req.body);  // リクエストボディの確認
    const response = await client.post(
      `${API_ENDPOINTS.FASTAPI}/api/gpt/api/generate-advice`,
      req.body,
      {
        headers: {
          ...req.headers,
          host: `${API_ENDPOINTS.FASTAPI}`,
        },
        withCredentials: true,
      }
    );

    console.log("Received response from FastAPI:", response.data);  // FastAPIからのレスポンスの確認

    res.status(response.status).json(response.data);
  } catch (error) {
    console.error("アドバイス生成中にエラーが発生しました:", error);
    console.error("Error details:", error.response?.data);  // エラーの詳細を出力
    if (error.response) {
      res.status(error.response.status).json(error.response.data);
    } else {
      res.status(500).json({ error: "アドバイス生成中にエラーが発生しました。" });
    }
  }
});

// セッション履歴取得エンドポイント
router.get("/session-history", async (req, res) => {
  try {
    // MongoDBから直接最新のセッションを取得

    const sessionData = await mongoose.connection
      .useDb('session_db')
      .collection(`sessions_${req.query.user_id}`)
      .findOne(
        {},
        { sort: { _id: -1 } }  // 最新のドキュメントを取得
      );

    console.log("取得したセッションデータ:", sessionData);

    if (sessionData && sessionData.data) {
      res.status(200).json(sessionData.data);
    } else {
      res.status(200).json({ messages: [] });
    }
  } catch (error) {
    console.error("セッション履歴の取得中にエラーが発生しました:", error);
    res.status(500).json({ error: "セッション履歴の取得に失敗しました。" });
  }
});

module.exports = router;