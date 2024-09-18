---

# Stripe Customer Search Lambda

このプロジェクトは、**AWS Lambda** 上で動作する **FastAPI** アプリケーションを使って、Stripe API を通じて顧客情報を検索するためのサービスです。AWS API Gateway を通じて公開され、特定のメールアドレスに基づいて Stripe の顧客情報を検索できます。

## 機能概要

- **Stripe API** を使用して、指定されたメールアドレスから顧客を検索
- 顧客情報をフラットな形式で返却し、ネストされたフィールドもすべて平坦化
- AWS Lambda 上で動作し、**FastAPI** を使用
- **Mangum** を使用して、AWS Lambda と FastAPI の統合を実現
- 入力されたメールアドレスがない場合、デフォルトのメールアドレスで検索

## 使い方

### 必要条件

- AWSアカウント
- Stripe API キー
- Python 3.9+
- AWS SAM CLI

### デプロイ手順

1. **リポジトリのクローン**

   ```bash
   git clone https://github.com/ユーザー名/リポジトリ名.git
   cd リポジトリ名
   ```

2. **依存関係のインストール**

   仮想環境を作成して、依存関係をインストールします。

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **AWS SAM を使用してビルドとデプロイ**

   AWS SAM を使用してアプリケーションをビルドし、AWS Lambda にデプロイします。

   ```bash
   sam build
   sam deploy --guided
   ```

   デプロイ時にいくつかの質問が表示されるため、スタック名やリージョンなどを指定します。`AWS_ACCESS_KEY_ID` と `AWS_SECRET_ACCESS_KEY` も必要です。

4. **API エンドポイントの確認**

   デプロイが成功すると、API Gatewayのエンドポイントが表示されます。これを使って API を呼び出すことができます。

### API の使用方法

#### エンドポイント

- `GET /search_customers`

#### クエリパラメータ

| パラメータ        | 説明                                                               |
| ----------------- | ------------------------------------------------------------------ |
| `api_key`         | Stripe APIキー                                                     |
| `email_addresses` | 検索するカンマ区切りのメールアドレスリスト。指定しない場合はデフォルトで `xxxxx@xxx.com` が使用されます。 |

#### 例

```bash
curl "https://your-api-endpoint.com/search_customers?api_key=your-stripe-api-key&email_addresses=test@example.com"
```

### レスポンス形式

APIは、以下のようなフラットな顧客情報の配列を返します。

```json
{
  "records": [
    {
      "object": "customer",
      "email": "test@example.com",
      "name": "テストユーザー",
      "address_city": "テストシティ",
      "metadata_サロン名": "テストサロン",
      "cus_id": "cus_ABC12345"
    }
  ]
}
```

### 開発環境の設定

#### ローカルでの実行

ローカル環境でサーバーを立ち上げるには、以下のコマンドを実行してください。

```bash
uvicorn main:app --reload
```

これで、`http://127.0.0.1:8000` でローカルサーバーが起動し、APIをテストできます。

### 注意事項

- Stripe API キーの管理には十分に注意してください。特に、公開リポジトリにキーをハードコーディングしないようにしてください。
- このアプリケーションは AWS Lambda 上で動作することを前提としており、ローカルでの開発は SAM CLI を使用することを推奨します。

## 技術スタック

- **Python 3.9**
- **FastAPI**
- **Mangum**（FastAPIとAWS Lambdaの統合）
- **Stripe API**

## ライセンス

このプロジェクトはMITライセンスのもとで公開されています。

---
