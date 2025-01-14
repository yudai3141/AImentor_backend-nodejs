const express = require("express");
const router = express.Router();
const axios = require('axios');
const { wrapper } = require('axios-cookiejar-support');
const tough = require('tough-cookie');
const User = require('../models/User');

// axiosインスタンスを作成し、クッキージャーを設定
const cookieJar = new tough.CookieJar();
const client = wrapper(axios.create({ jar: cookieJar }));

// 週次ミーティング開始
router.post("/start", async (req, res) => {
  try {
    const response = await client.post(
      'http://localhost:8001/weekly-chat/start',
      req.body,
      {
        headers: {
          ...req.headers,
          host: 'localhost:8001',
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
    console.error("FastAPIサーバーとの通信中にエラーが発生しました:", error);
    if (error.response) {
      res.status(error.response.status).json(error.response.data);
    } else {
      res.status(500).json({ error: "FastAPIサーバーとの通信中にエラーが発生しました。" });
    }
  }
});

// 週次ミーティングメッセージ
router.post("/", async (req, res) => {
  try {
    const response = await client.post(
      'http://localhost:8001/weekly-chat',
      req.body,
      {
        headers: {
          ...req.headers,
          host: 'localhost:8001',
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
    console.error("FastAPIサーバーとの通信中にエラーが発生しました:", error);
    if (error.response) {
      res.status(error.response.status).json(error.response.data);
    } else {
      res.status(500).json({ error: "FastAPIサーバーとの通信中にエラーが発生しました。" });
    }
  }
});

// 現在時刻を取得する関数
const getCurrentTime = () => {
  return new Date();
};

router.put('/users/:userId/weekly-update', async (req, res) => {
  try {
    const { userId } = req.params;
    const { goalIndex, weeklyMeetings, advice } = req.body;

    const user = await User.findById(userId);
    if (!user) {
      return res.status(404).json({ message: 'User not found' });
    }

    // 週次ミーティングの完了状態とアドバイスを更新
    user.shortTerm_goals[goalIndex].weeklyMeetings = weeklyMeetings;
    user.shortTerm_goals[goalIndex].advice = advice;

    await user.save();
    res.json({ 
      message: 'Weekly progress updated successfully',
      shortTerm_goals: user.shortTerm_goals
    });
  } catch (error) {
    console.error('Weekly update error:', error);
    res.status(500).json({ message: 'Internal server error' });
  }
});

// アドバイス生成エンドポイント
router.post("/generate-advice", async (req, res) => {
  try {
    const response = await client.post(
      'http://localhost:8001/generate-advice',
      req.body,
      {
        headers: {
          ...req.headers,
          host: 'localhost:8001',
        },
        withCredentials: true,
      }
    );

    res.status(response.status).json(response.data);
  } catch (error) {
    console.error("アドバイス生成中にエラーが発生しました:", error);
    res.status(500).json({ error: "アドバイス生成中にエラーが発生しました。" });
  }
});

module.exports = router; 