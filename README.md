# Stripe 顧客・サブスクリプション・請求情報検索API

## 概要
このプロジェクトは、FastAPIを使用してStripeの顧客、サブスクリプション、請求、インボイス情報を検索し、それらのデータをフラット化してJSON形式で返すAPIです。AWS Lambdaでの実行を想定しており、複数のIDによる一括検索にも対応しています。

## 主要機能
1. 顧客情報の検索：メールアドレスから顧客情報を取得
2. サブスクリプション情報の検索：顧客IDからサブスクリプション情報を取得
3. サブスクリプションアイテム情報の検索：サブスクリプションIDからアイテム情報とプロダクト情報を取得
4. 請求情報の検索：サブスクリプションIDから関連する請求情報を取得
5. インボイス情報の検索：サブスクリプションIDから関連するインボイス情報を取得
6. 請求IDからインボイス情報の検索：請求IDから関連するインボイス情報を取得

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
      "address_city": "Tokyo",
      "address_country": "Japan",
      "created": "2023/01/01 09:00:00"
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
      "plan_amount": 5000,
      "plan_currency": "jpy",
      "plan_interval": "month"
    }
  ]
}
```

### 3. サブスクリプションアイテム情報の検索

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
      "product_description": "This is a test product",
      "product_active": true
    },
    {
      "id": "si_yyyy",
      "subscription": "sub_yyyy",
      "price_product": "prod_yyyy",
      "product_name": "Another Product",
      "price_amount": 2000,
      "currency": "jpy",
      "product_description": "This is another test product",
      "product_active": true
    }
  ]
}
```

### 4. 請求情報の検索

#### URL

`GET /search_charges_by_subscription`

#### パラメータ

- `api_key`: StripeのAPIキー（必須）
- `subscription_ids`: カンマ区切りのサブスクリプションID（省略可能、デフォルト: `"sub_1OOVw0APdno01lSPQNcrQCSC"`）


#### レスポンス例

```json
{
  "records": [
    {
      "id": "ch_xxxx",
      "amount": 5000,
      "currency": "jpy",
      "customer": "cus_xxxx",
      "description": "Subscription charge",
      "invoice": "in_xxxx",
      "paid": true,
      "status": "succeeded",
      "created": "2023/05/01 10:00:00"
    }
  ]
}
```

### 5. インボイス情報の検索

#### URL

`GET /search_invoices_by_subscription`

#### パラメータ

- `api_key`: StripeのAPIキー（必須）
- `subscription_ids`: カンマ区切りのサブスクリプションID（省略可能、デフォルト: `"sub_1OOVw0APdno01lSPQNcrQCSC"`）


#### レスポンス例

```json
{
  "records": [
    {
      "id": "in_xxxx",
      "customer": "cus_xxxx",
      "subscription": "sub_xxxx",
      "status": "paid",
      "total": 5000,
      "currency": "jpy",
      "created": "2023/05/01 09:55:00",
      "period_start": "2023/05/01 00:00:00",
      "period_end": "2023/06/01 00:00:00"
    }
  ]
}
```

### 6. 請求IDからインボイス情報の検索

#### URL

`GET /search_invoice_by_charge`

#### パラメータ

- `api_key`: StripeのAPIキー（必須）
- `charge_ids`: カンマ区切りの請求ID（必須）


#### レスポンス例

```json
{
  "records": [
    {
      "id": "in_yyyy",
      "charge": "ch_xxxx",
      "customer": "cus_xxxx",
      "subscription": "sub_xxxx",
      "status": "paid",
      "total": 5000,
      "currency": "jpy",
      "created": "2023/05/01 09:55:00",
      "period_start": "2023/05/01 00:00:00",
      "period_end": "2023/06/01 00:00:00",
      "lines": [
        {
          "description": "Monthly subscription fee",
          "amount": 5000,
          "currency": "jpy"
        }
      ]
    }
  ]
}
```

## インストール方法

1. リポジトリをクローンします：

```plaintext
git clone https://github.com/yourusername/your-repo-name.git
cd your-repo-name
```


2. 仮想環境を作成し、アクティベートします：

```plaintext
python -m venv venv
source venv/bin/activate  # Windowsの場合: venv\Scripts\activate
```


3. 必要なパッケージをインストールします：

```plaintext
pip install -r requirements.txt
```




## 使用方法

1. ローカルでの実行：

```plaintext
uvicorn main:app --reload
```


2. ブラウザで `http://127.0.0.1:8000/docs` にアクセスすると、Swagger UIでAPIドキュメントを確認できます。


## 環境設定

- StripeのAPIキーは、各エンドポイントのクエリパラメータとして渡します。セキュリティ上の理由から、環境変数としての設定は避けています。
- タイムゾーンはJST（日本標準時）に設定されています。


## エラーハンドリングとログ

- すべてのエンドポイントで適切なエラーハンドリングを実装しています。
- エラーはHTTPステータスコードとともに返され、詳細なエラーメッセージが提供されます。
- ログはPythonの標準ロギングモジュールを使用して記録されます。


## デプロイ方法（AWS Lambda）

このプロジェクトは、AWS LambdaおよびAPI Gatewayでデプロイされることを想定しています。デプロイにはSAM CLIを使用します。

1. AWS CLIをインストールし、設定します。
2. SAM CLIをインストールします。
3. `template.yaml` ファイルを作成し、Lambda関数とAPI Gatewayの設定を記述します。
4. 以下のコマンドでビルドとデプロイを行います：

```plaintext
sam build
sam deploy --guided
```


5. デプロイ後、提供されるAPIエンドポイントURLを使用してAPIにアクセスできます。


## ライセンス

このプロジェクトは[MITライセンス](LICENSE)の下で公開されています。

## 注意事項

- このAPIを使用する際は、Stripeの利用規約とデータ保護ポリシーを遵守してください。
- 本番環境で使用する前に、十分なテストを行ってください。
- APIキーは安全に管理し、公開リポジトリにコミットしないよう注意してください。
