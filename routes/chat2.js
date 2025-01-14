const express = require("express");
const router = express.Router();
const axios = require('axios');
const { wrapper } = require('axios-cookiejar-support');
const tough = require('tough-cookie');

// axiosインスタンスを作成し、クッキージャーを設定
const cookieJar = new tough.CookieJar();
const client = wrapper(axios.create({ jar: cookieJar }));

router.post("/", async (req, res) => {
  try {
    // FastAPIサーバーにリクエストを転送
    const response = await client.post(
      'http://localhost:8000/api/gpt',
      req.body,
      {
        headers: {
          ...req.headers,
          host: 'localhost:8000',
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
      'http://localhost:8001/generate-advice',
      req.body,
      {
        headers: {
          ...req.headers,
          host: 'localhost:8000',
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

module.exports = router;