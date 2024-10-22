const express = require("express");
const app = express();
const userRoute = require("./routes/users");
const authRoute = require("./routes/auth");
const chatRoute = require("./routes/chat");
const PORT = 5002; 
const mongoose = require("mongoose");
const cors = require("cors");
require("dotenv").config();
const path = require("path");


app.use(express.json());
app.use(cors()); 

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
app.use("/api/chat", chatRoute);

app.get("/", (req,res) => {
    res.send("hello express");
});


app.listen(PORT, () => console.log("サーバーが起動しました"));