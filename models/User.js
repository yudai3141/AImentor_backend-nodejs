const mongoose = require("mongoose");

// タスクのサブスキーマを定義
const TaskSchema = new mongoose.Schema({
    title: { type: String, required: true },
    completed: { type: Boolean, default: false },
    importance: { type: Number, enum: [1, 2, 3], default: 2 },
    status: { type: String, enum: ['not_started', 'in_progress', 'completed'], default: 'not_started' }
});

// 短期目標のサブスキーマを定義
const ShortTermGoalSchema = new mongoose.Schema({
    shortTerm_goal: { type: String, required: true },
    KPI: { type: String },
    numerical_or_TF: { type: String, enum: ["numerical", "TF"] },
    KPI_indicator: { type: Number },
    weekly_goal_num: {type: Number},
    current_achievement_num: { type: Number, default: 0 },
    weekly_goal_num: { type: Number, default: 0 },
    importance: { type: Number, enum: [1, 2, 3], default: 2 },
    status: { type: String, enum: ['not_started', 'in_progress', 'completed'], default: 'not_started' },
    tasks: [TaskSchema],
    weeklyMeetings: {
        type: [Boolean],
        default: [false, false, false, false]
    },
    advice: { type: String, default: '' }
});

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
    longTerm_goal_deadline: {
        type: Date,
        default: null
    },
    shortTerm_goals: [ShortTermGoalSchema],
    isAdmin: {
        type: Boolean,
        default: false,
    },
    advice: {
        type: String,
        default: ''
    },
    weeklyAchievements: {
        week1: { type: Number, default: 0 },
        week2: { type: Number, default: 0 },
        week3: { type: Number, default: 0 },
        week4: { type: Number, default: 0 }
    },
    weeklyAvailableTime: {
        week1: { type: Number, default: 0 },
        week2: { type: Number, default: 0 },
        week3: { type: Number, default: 0 },
        week4: { type: Number, default: 0 }
    },
    conversation_history: [{
        timestamp: Date,
        goal: Object,
        messages: [{
            role: String,
            content: String
        }]
    }],
    success_experiences: [String],
    failure_experiences: [String],
    high_level_insights: [String],
    last_analyzed: Date,
    mainGoalStartDate: Date
},
{ timestamps: true }
);

module.exports = mongoose.model("User", UserSchema);