const mongoose = require('mongoose');
const User = require('../models/User');
require('dotenv').config();

async function updateSchema() {
  try {
    // MongoDBに接続
    await mongoose.connect(process.env.MONGOURL);
    console.log('Connected to MongoDB');

    // 全ユーザーを取得
    const users = await User.find({});
    console.log(`Found ${users.length} users to update`);

    for (const user of users) {
      let isModified = false;

      // 各小目標をチェック
      user.shortTerm_goals.forEach(goal => {
        // adviceフィールドが存在しない場合は追加
        if (!goal.advice) {
          goal.advice = '';
          isModified = true;
        }

        // weekly_goal_numフィールドが存在しない場合は追加
        if (goal.weekly_goal_num === undefined) {
          goal.weekly_goal_num = 0;
          isModified = true;
        }
      });

      // 会話履歴と分析関連のフィールドを追加
      if (!user.conversation_history) {
        user.conversation_history = [];
        isModified = true;
      }
      
      // 分析結果のフィールドを文字列配列型に変更
      if (!Array.isArray(user.success_experiences)) {
        user.success_experiences = [];
        isModified = true;
      }
      
      if (!Array.isArray(user.failure_experiences)) {
        user.failure_experiences = [];
        isModified = true;
      }
      
      if (!Array.isArray(user.high_level_insights)) {
        user.high_level_insights = [];
        isModified = true;
      }
      
      if (!user.last_analyzed) {
        user.last_analyzed = null;
        isModified = true;
      }

      // 変更があった場合のみ保存
      if (isModified) {
        await user.save();
        console.log(`Updated user: ${user.username}`);
      }
    }

    console.log('Schema update completed successfully');
  } catch (error) {
    console.error('Error updating schema:', error);
  } finally {
    // データベース接続を閉じる
    await mongoose.connection.close();
    console.log('Database connection closed');
  }
}

// スクリプトを実行
updateSchema(); 