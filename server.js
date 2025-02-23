const express = require("express");
const app = express();
const userRoute = require("./routes/users");
const authRoute = require("./routes/auth");
const chat2Route = require("./routes/chat2");
const weeklyRoute = require("./routes/weekly_chat");
const PORT = 5002; 
const mongoose = require("mongoose");
const cors = require("cors");
require("dotenv").config();
const path = require("path");


app.use(express.json());

// CORSミドルウェアの設定
app.use(cors({
    origin: ["http://localhost:3000", "https://ai-mentor-frontend.vercel.app"],
    credentials: true,
    methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
    allowedHeaders: ['Content-Type', 'Authorization']
}));


//DB接続
mongoose.connect(process.env.MONGOURL)
.then(() => {
    console.log("DBと接続中・・・");
}).catch((err) => {
    console.error("MongoDB接続エラー:", err.message);
});

// ミドルウェア
app.use(express.json());
app.use("/api/users", userRoute);
app.use("/api/auth", authRoute);
app.use("/api/chat2", chat2Route);
app.use("/api/weekly-chat", weeklyRoute);

app.get("/", (req,res) => {
    res.send("hello express");
});

// ポート設定
const port = process.env.PORT || 8080;

app.listen(port, '0.0.0.0', () => {
  console.log(`Server is running on port ${port}`);
});