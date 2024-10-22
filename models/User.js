const mongoose = require("mongoose");

const UserSchema = new mongoose.Schema({
    username: {
        type: String,
        required: true,
        max: 20
    },
    email: {
        type: String,
        required: true,
        max: 500,
        unique: true,
    },
    password: {
        type: String,
        required: true,
        min: 6,
        max: 20
    },
    longTerm_goal: {
        type: String,
        default: ""
    },
    shortTerm_goals: {
        type: Array,
        default: [],
    },
    isAdmin: {
        type: Boolean,
        default: false,
    },
},
{timestamps: true}
);

module.exports = mongoose.model("User", UserSchema)