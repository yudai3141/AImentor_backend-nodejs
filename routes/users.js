const express = require("express");
const router = express.Router();
const User = require("../models/User")
const { API_ENDPOINTS } = require('../config/constants');

//　ユーザー情報の更新
router.put("/:id", async(req,res) => {
    if(req.body.userId === req.params.id || req.body.isAdmin) {
        try {
            const user = await User.findByIdAndUpdate(req.params.id,{
                $set: req.body,
            });
            res.status(200).json("ユーザー情報が更新されました")
        }
        catch(e) {
            return res.status(500).json(e);
        }
    }
    else {
        return res.status(403).json("あなたは自分のアカウントの時のみ情報を更新できます")
    }
})

//　ユーザー情報の更新
router.put("/insights/:id", async(req,res) => {
    if(req.body.userId === req.params.id || req.body.isAdmin) {
        try {
            const updateData = {};
            const pushData = {};
            
            // 会話履歴の更新
            if (req.body.conversation_history) {
                updateData.conversation_history = req.body.conversation_history;
            }
            
            // 分析結果の更新（配列に追加）
            if (req.body.success_experiences) {
                pushData.success_experiences = req.body.success_experiences;
            }
            if (req.body.failure_experiences) {
                pushData.failure_experiences = req.body.failure_experiences;
            }
            if (req.body.high_level_insights) {
                pushData.high_level_insights = req.body.high_level_insights;
            }
            if (req.body.last_analyzed) {
                updateData.last_analyzed = req.body.last_analyzed;
            }

            console.log("=== DB更新データ ===");
            console.log("$set:", updateData);
            console.log("$push:", pushData);

            // $setと$pushを別々に実行
            const user = await User.findByIdAndUpdate(
                req.params.id,
                {
                    ...(Object.keys(updateData).length > 0 && { $set: updateData }),
                    ...(Object.keys(pushData).length > 0 && { $push: pushData })
                },
                { new: true }
            );

            res.status(200).json("ユーザー情報が更新されました");
        } catch(e) {
            console.error("DB更新エラー:", e);
            return res.status(500).json(e);
        }
    } else {
        return res.status(403).json("あなたは自分のアカウントの時のみ情報を更新できます");
    }
});

//　ユーザー情報の削除
router.delete("/:id", async(req,res) => {
    if(req.body.userId === req.params.id || req.body.isAdmin) {
        try {
            const user = await User.findByIdAndDelete(req.params.id);
            res.status(200).json("ユーザー情報が削除されました")
        }
        catch(e) {
            return res.status(500).json(e);
        }
    }
    else {
        return res.status(403).json("あなたは自分のアカウントの時のみ情報を削除できます")
    }
})

//クエリでuser情報を取得
router.get("/", async (req, res) => {
    const userId = req.query.userId;
    const username = req.query.username;
    try {
      const user = userId
        ? await User.findById(userId)
        : await User.findOne({ username: username });
      
      // 会話履歴を適切に展開
      if (user.conversation_history && user.conversation_history.length > 0) {
          user.conversation_history = user.conversation_history.map(history => ({
              ...history.toObject(),
              messages: history.messages || []
          }));
      }
      
      const { password, updatedAt, ...other } = user._doc;
      return res.status(200).json(other);
    } catch (err) {
      console.error("Error in GET /users:", err);  // エラーの詳細を確認
      return res.status(500).json(err);
    }
});



module.exports = router;