FROM --platform=linux/amd64 node:18-slim

WORKDIR /app

# package.jsonとpackage-lock.jsonをコピー
COPY package*.json ./

# 依存関係のインストール
RUN npm install

# アプリケーションのコピー
COPY . .

# 環境変数の設定
ENV PORT=8080
ENV MONGOURL=mongodb+srv://hondayudai:7TXg0cuQy2TWJXTZ@cluster0.uzwho.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0

# ポートを公開
EXPOSE 8080

# アプリケーションの起動
CMD ["npm", "start"] 