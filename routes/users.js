const express = require("express");
const router = express.Router();
const User = require("../models/User")

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
      
    //   console.log("Found user:", user);  // ユーザーデータ全体を確認
    //   console.log("ShortTerm goals:", user.shortTerm_goals);  // shortTerm_goalsの内容を確認
      
      const { password, updatedAt, ...other } = user._doc;
      return res.status(200).json(other);
    } catch (err) {
      console.error("Error in GET /users:", err);  // エラーの詳細を確認
      return res.status(500).json(err);
    }
});



module.exports = router;