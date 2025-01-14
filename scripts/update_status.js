const mongoose = require("mongoose");
const User = require("../models/User");
const path = require('path');
require('dotenv').config({ path: path.resolve(__dirname, '../.env') });

// 環境変数が読み込めているか確認
console.log('MONGOURL:', process.env.MONGOURL);

// MongoDBに接続
if (!process.env.MONGOURL) {
    console.error('Error: MONGOURL environment variable is not set');
    process.exit(1);
}

mongoose.connect(process.env.MONGOURL, {
    useNewUrlParser: true,
    useUnifiedTopology: true,
}).then(() => {
    console.log('Successfully connected to MongoDB.');
}).catch((err) => {
    console.error('Error connecting to MongoDB:', err);
    process.exit(1);
});

async function updateStatus() {
    try {
        // 全ユーザーを取得
        const users = await User.find({});

        for (const user of users) {
            // 各ユーザーの短期目標を更新
            if (user.shortTerm_goals) {
                user.shortTerm_goals = user.shortTerm_goals.map(goal => {
                    // 既存のデータを全て展開して保持
                    return {
                        ...goal,
                        status: goal.status || 'not_started',  // statusがなければ追加
                        weekly_goal_num: goal.weekly_goal_num || 0,  // 週ごとの目標値を追加
                        tasks: goal.tasks ? goal.tasks.map(task => ({
                            ...task,
                            status: task.status || 'not_started'  // 各タスクにもstatusがなければ追加
                        })) : []
                    };
                });

                // 変更を保存
                await user.save();
                console.log(`Updated user: ${user.username}`);
            }
        }

        console.log('Status update completed');
        process.exit(0);
    } catch (error) {
        console.error('Error updating status:', error);
        process.exit(1);
    }
}

updateStatus(); 