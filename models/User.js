const mongoose = require("mongoose");

// タスクのサブスキーマを定義
const TaskSchema = new mongoose.Schema({
    title: { type: String, required: true },
    completed: { type: Boolean, default: false },
}, { _id: false });

// 短期目標のサブスキーマを定義
const ShortTermGoalSchema = new mongoose.Schema({
    title: { type: String, required: true },
    KPI: { type: String },
    isNumerical: {type: Boolean},
    tasks: [TaskSchema],  // タスクを子要素として含める
    max_achievement_num: {type: Number},
    current_achievement_num: {type: Number, default: 0 }
}, { _id: false });

const UserSchema = new mongoose.Schema({
    username: {
        type: String,
        required: true,
        maxlength: 20
    },
    email: {
        type: String,
        required: true,
        maxlength: 500,
        unique: true,
    },
    password: {
        type: String,
        required: true,
        minlength: 6,
        maxlength: 20
    },
    longTerm_goal: {
        type: String,
        default: ""
    },
    shortTerm_goals: [ShortTermGoalSchema],  // 短期目標の配列
    isAdmin: {
        type: Boolean,
        default: false,
    },
},
{ timestamps: true }
);

module.exports = mongoose.model("User", UserSchema);