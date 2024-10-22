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
      const { password, updatedAt, ...other } = user._doc;
      return res.status(200).json(other);
    } catch (err) {
      return res.status(500).json(err);
    }
  });

//ユーザーのフォロー
router.put("/:id/follow", async(req, res) => {
    if (req.body.userId !== req.params.id) {
        try {
            const user = await User.findById(req.params.id);
            const currentUser = await User.findById(req.body.userId);
            if (!user.followers.includes(req.body.userId)) {
                // フォロワーに自分がいなければフォロー可能
                await user.updateOne({
                    $push: {
                        followers: req.body.userId
                    }
                })
                await currentUser.updateOne({
                    $push: {
                        followings: req.params.id
                    }
                })
                return res.status(200).json("フォローに成功しました！")
            } else {
                return res.status(403).json("あなたは既にこのユーザーをフォローしています")
            }
        } catch(e) {
            return res.status(500).json(e);
        }
    } else {
        return res.status(500).json("自分自身をフォローできません")
    }
})

// ユーザーのフォローを外す
router.put("/:id/unfollow", async(req, res) => {
    if (req.body.userId !== req.params.id) {
        try {
            const user = await User.findById(req.params.id);
            const currentUser = await User.findById(req.body.userId);
            if (user.followers.includes(req.body.userId)) {
                // フォロワーに自分がいればフォロー解除可能
                await user.updateOne({
                    $pull: {
                        followers: req.body.userId
                    }
                })
                await currentUser.updateOne({
                    $pull: {
                        followings: req.params.id
                    }
                })
                return res.status(200).json("フォロー解除に成功しました！")
            } else {
                return res.status(403).json("あなたはこのユーザーをフォローしていません。")
            }
        } catch(e) {
            return res.status(500).json(e);
        }
    } else {
        return res.status(500).json("自分自身をフォロー解除できません")
    }
})

module.exports = router;