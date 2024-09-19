---

# Stripe 顧客およびサブスクリプション検索API

このプロジェクトは、FastAPIを使用してStripeの顧客およびサブスクリプション情報を検索し、それらのデータをフラット化してJSON形式で返すAPIです。サブスクリプションに関連するプロダクト情報も含めて取得する機能を提供します。

## 機能

1. **顧客情報の検索**: 顧客のメールアドレスを指定して、対応する顧客情報をStripeから取得し、フラット化して返します。
2. **サブスクリプション情報の検索**: 顧客IDを指定して、顧客に紐づくサブスクリプション情報を取得し、フラット化して返します。
3. **サブスクリプションIDでアイテム情報の検索**: サブスクリプションIDを指定して、そのサブスクリプションに関連するアイテム情報を取得し、プロダクト情報も含めてフラット化して返します。

## エンドポイント

### 1. 顧客情報の検索
#### URL
`GET /search_customers`

#### パラメータ
- `api_key`: StripeのAPIキー（必須）
- `email_addresses`: カンマ区切りのメールアドレス（省略可能、デフォルト: `"hori@revol.co.jp"`）

#### レスポンス例
```json
{
  "records": [
    {
      "cus_id": "cus_xxxx",
      "email": "example@example.com",
      "name": "John Doe",
      "phone": "+1234567890",
      ...
    }
  ]
}
```

### 2. サブスクリプション情報の検索
#### URL
`GET /search_subscriptions`

#### パラメータ
- `api_key`: StripeのAPIキー（必須）
- `cus_ids`: カンマ区切りの顧客ID（省略可能、デフォルト: `"cus_PCvnk7s61noGQW"`）

#### レスポンス例
```json
{
  "records": [
    {
      "id": "sub_xxxx",
      "customer": "cus_xxxx",
      "status": "active",
      "current_period_start": "2024/09/18 00:00:00",
      "current_period_end": "2024/10/18 00:00:00",
      ...
    }
  ]
}
```

### 3. サブスクリプションIDでアイテム情報の検索
#### URL
`GET /search_subscription_items`

#### パラメータ
- `api_key`: StripeのAPIキー（必須）
- `subscription_ids`: カンマ区切りのサブスクリプションID（省略可能、デフォルト: `"sub_1OOVw0APdno01lSPQNcrQCSC"`）

#### レスポンス例
```json
{
  "records": [
    {
      "id": "si_xxxx",
      "subscription": "sub_xxxx",
      "price_product": "prod_xxxx",
      "product_name": "Test Product",
      "price_amount": 1000,
      "currency": "jpy",
      ...
    },
    {
      "id": "si_yyyy",
      "subscription": "sub_yyyy",
      "price_product": "prod_yyyy",
      "product_name": "Another Product",
      "price_amount": 2000,
      "currency": "jpy",
      ...
    }
  ]
}

```

## インストール方法

1. リポジトリをクローンします。
    ```bash
    git clone https://github.com/your-username/your-repo-name.git
    cd your-repo-name
    ```

2. 必要な依存パッケージをインストールします。
    ```bash
    pip install -r requirements.txt
    ```

3. FastAPIサーバーを起動します。
    ```bash
    uvicorn main:app --reload
    ```

4. ブラウザで `http://127.0.0.1:8000/docs` にアクセスすると、SwaggerによるAPIドキュメントを確認できます。

## 環境変数

StripeのAPIキーはクエリパラメータとして渡されます。

## デプロイ方法

このプロジェクトは、AWS LambdaおよびAPI Gatewayでデプロイされることを想定しています。デプロイにはSAM CLIを使用します。

### 1. SAM CLIを使ったビルドとデプロイ

```bash
sam build
sam deploy --guided
```

## ライセンス

このプロジェクトはMITライセンスの下で提供されています。

---
