---

# Stripe Customer and Subscription Search API

このプロジェクトは、**AWS Lambda** 上で動作する **FastAPI** アプリケーションを使用して、**Stripe** 顧客情報およびサブスクリプション情報を検索するためのAPIです。**AWS API Gateway** を通じて公開され、メールアドレスまたは顧客IDをもとに顧客およびサブスクリプション情報を検索します。

## 機能概要

- メールアドレスから顧客情報を取得
- 顧客IDからサブスクリプション情報を取得
- 検索結果はフラットな形式で返され、ネストされたフィールドが平坦化されます
- パラメータが空の場合、デフォルトのメールアドレスや顧客IDで検索

## エンドポイント

### 1. 顧客情報検索: `/search_customers`

- メールアドレスを基に顧客情報を検索します。
- **クエリパラメータ**: `api_key`（Stripe APIキー）、`email_addresses`（カンマ区切りのメールアドレス）
- **デフォルト動作**: `email_addresses` が指定されていない場合、`hori@revol.co.jp` をデフォルトで検索します。

#### 例

```bash
curl "https://your-api-endpoint.com/search_customers?api_key=your-stripe-api-key&email_addresses=test@example.com"
```

#### パラメータ詳細

| パラメータ        | 説明                                                               |
| ----------------- | ------------------------------------------------------------------ |
| `api_key`         | Stripe APIキー                                                     |
| `email_addresses` | カンマ区切りのメールアドレス（指定がない場合、`hori@revol.co.jp` が使用されます） |

#### レスポンス例

```json
{
  "records": [
    {
      "object": "customer",
      "email": "test@example.com",
      "cus_id": "cus_ABC12345",
      "name": "テストユーザー",
      "address_city": "テストシティ",
      "metadata_サロン名": "テストサロン"
      // その他のフラットな顧客情報
    }
  ]
}
```

### 2. サブスクリプション検索: `/search_subscriptions`

- 顧客IDを基にサブスクリプション情報を検索します。
- **クエリパラメータ**: `api_key`（Stripe APIキー）、`cus_ids`（カンマ区切りの顧客ID）
- **デフォルト動作**: `cus_ids` が指定されていない場合、`cus_PCvnk7s61noGQW` をデフォルトで検索します。

#### 例

```bash
curl "https://your-api-endpoint.com/search_subscriptions?api_key=your-stripe-api-key&cus_ids=cus_ABC12345,cus_DEF67890"
```

#### パラメータ詳細

| パラメータ | 説明                                                            |
| ---------- | --------------------------------------------------------------- |
| `api_key`  | Stripe APIキー                                                   |
| `cus_ids`  | カンマ区切りの顧客ID（指定がない場合、`cus_PCvnk7s61noGQW` が使用されます） |

#### レスポンス例

```json
{
  "records": [
    {
      "object": "subscription",
      "cus_id": "cus_ABC12345",
      "status": "active",
      "items": "プロダクト1, プロダクト2",
      "start_date": 1609459200,
      "current_period_end": 1612137600
      // その他のフラットなサブスクリプション情報
    }
  ]
}
```

## セットアップ

### 必要条件

- AWSアカウント
- Stripe APIキー
- Python 3.9+
- AWS SAM CLI

### プロジェクトのクローン

リポジトリをクローンして、プロジェクトディレクトリに移動します。

```bash
git clone https://github.com/your-username/stripe-customer-subscription-search.git
cd stripe-customer-subscription-search
```

### 依存関係のインストール

仮想環境を作成し、必要な依存関係をインストールします。

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### デプロイ手順

AWS SAM CLI を使用して Lambda にデプロイします。

1. ビルド

   ```bash
   sam build
   ```

2. デプロイ

   ```bash
   sam deploy --guided
   ```

3. デプロイ後、API Gatewayエンドポイントが表示されます。

### ローカルでの実行

ローカル環境でFastAPIを実行してテストできます。

```bash
uvicorn main:app --reload
```

## 開発環境

- **Python 3.9**
- **FastAPI**
- **Mangum**（AWS Lambda と FastAPI の統合）
- **Stripe API**

## ライセンス

このプロジェクトはMITライセンスのもとで公開されています。

---

### 説明

- **機能概要**: このプロジェクトの機能を説明し、APIエンドポイントの使い方を詳細に記載しています。
- **使い方**: クローンから依存関係のインストール、デプロイ手順までのセットアップ方法を示しています。
- **エンドポイントの使用方法**: 顧客情報とサブスクリプション情報を検索するためのAPIエンドポイントを説明しています。

## エンドポイント
https://o9e8gvcjdh.execute-api.ap-northeast-1.amazonaws.com/prod/
## Lambda
https://ap-northeast-1.console.aws.amazon.com/lambda/home?region=ap-northeast-1#/functions/stripe-customer-search-lambda-FastApiFunction-6HzYFQP389Nb/aliases/production?tab=configure
