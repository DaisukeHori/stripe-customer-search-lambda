---

# Stripe 顧客・サブスクリプション・請求情報検索API

## 概要

このプロジェクトは、**FastAPI**を使用して構築された、Stripeの顧客、サブスクリプション、請求、インボイス情報を検索するためのAPIです。取得したデータをフラット化し、JSON形式で返すことで、データの取り扱いを容易にします。AWS Lambda上での実行を想定しており、大量のIDに対する一括検索にも対応しています。  
さらに、**各種Stripeオブジェクト（Customer, Subscription, Charge, Invoiceなど）の`id`フィールド**を、**オブジェクトごとに`???_id`へリネームして返却**する機能を追加しています。

## 目次

- [主要機能](#主要機能)
- [アーキテクチャ](#アーキテクチャ)
- [エンドポイント詳細](#エンドポイント詳細)
  - [1. 顧客情報の検索](#1-顧客情報の検索)
  - [2. サブスクリプション情報の検索](#2-サブスクリプション情報の検索)
  - [3. サブスクリプションアイテム情報の検索](#3-サブスクリプションアイテム情報の検索)
  - [4. 請求情報の検索](#4-請求情報の検索)
  - [5. インボイス情報の検索](#5-インボイス情報の検索)
  - [6. 請求IDからインボイス情報の検索](#6-請求idからインボイス情報の検索)
  - [7. サブスクリプションIDからサブスクリプション情報の直接検索](#7-サブスクリプションidからサブスクリプション情報の直接検索)
  - [8. フルデータ検索 (search_subscriptions_fulldata)](#8-フルデータ検索-search_subscriptions_fulldata)
- [インストール方法](#インストール方法)
- [環境設定](#環境設定)
- [使用方法](#使用方法)
- [リクエストとレスポンスの例](#リクエストとレスポンスの例)
- [エラーハンドリング](#エラーハンドリング)
- [テスト方法](#テスト方法)
- [デプロイ方法（AWS Lambda）](#デプロイ方法aws-lambda)
- [セキュリティと認証](#セキュリティと認証)
- [ログとモニタリング](#ログとモニタリング)
- [制限事項と考慮点](#制限事項と考慮点)
- [貢献方法](#貢献方法)
- [ライセンス](#ライセンス)
- [注意事項](#注意事項)
- [FAQ](#faq)
- [お問い合わせ](#お問い合わせ)

## 主要機能

1. **顧客情報の検索**：メールアドレスから顧客情報を取得します。  
2. **サブスクリプション情報の検索**：顧客IDからサブスクリプション情報を取得します。  
3. **サブスクリプションアイテム情報の検索**：サブスクリプションIDからアイテム情報と関連するプロダクト情報を取得します。  
4. **請求情報の検索 (Charges)**：サブスクリプションIDから関連する請求情報を取得します。  
5. **インボイス情報の検索**：サブスクリプションIDから関連するインボイス情報を取得します。  
6. **請求IDからインボイス情報の検索**：請求IDから関連するインボイス情報を取得します。  
7. **サブスクリプションIDからサブスクリプション情報の直接検索**：複数のサブスクリプションIDを一括で指定し、結果をフラット化したJSON形式で返します。  
8. **フルデータ検索 (search_subscriptions_fulldata)**：顧客IDからサブスクリプション全情報を取得し、商品名や次回請求プレビューなどの詳細をまとめて返却します。  

### 変更点: `id`のリネーム

Stripeのオブジェクトに含まれる `id` フィールドは、オブジェクトごとに以下の形式にリネームされます。

- **Customer**: `id` → `cus_id`
- **Subscription**: `id` → `sub_id`
- **SubscriptionItem**: `id` → `si_id`
- **Invoice**: `id` → `inv_id`
- **Charge**: `id` → `ch_id`
- **Product**: `id` → `prod_id`
- **Price**: `id` → `price_id`
- **Plan**: `id` → `plan_id`

すべてのエンドポイントで返却されるJSONでは、元々の `id` フィールドが上記のように置換された状態で出力されるため、アプリケーション側での取り扱いが容易になります。

## アーキテクチャ

- **フレームワーク**：FastAPIを使用してAPIエンドポイントを構築しています。  
- **デプロイ環境**：AWS LambdaおよびAPI Gatewayでのサーバーレス環境を想定しています。  
- **データ取得**：StripeのPython SDKを使用してAPIからデータを取得します。  
- **データ処理**：取得したネストされたJSONデータをフラット化し、扱いやすい形式で提供します。  
- **タイムゾーン**：すべての日時情報はJST（日本標準時）に変換されています。  

## エンドポイント詳細

各エンドポイントは`GET`リクエストを受け付けます。以下に詳細を示します。  
**共通事項**: すべてのJSON出力において、Stripeオブジェクトの `id` が `???_id` に置き換わる点にご留意ください。  

---

### 1. 顧客情報の検索

#### URL

```
GET /search_customers
```

#### パラメータ

- `api_key` (必須): StripeのAPIキー。  
- `email_addresses` (オプション): カンマ区切りのメールアドレス。指定がない場合、デフォルトで`"hori@revol.co.jp"`が使用されます。

#### 機能説明

指定されたメールアドレスに対応する顧客情報を取得します。メールアドレスは複数指定可能で、一度に大量の顧客情報を取得できます。

#### リクエスト例

```bash
curl -X GET "http://127.0.0.1:8000/search_customers?api_key=sk_test_4eC39HqLyjWDarjtT1zdp7dc&email_addresses=example1@example.com,example2@example.com"
```

#### レスポンス例

```json
{
  "records": [
    {
      "cus_id": "cus_1234567890",
      "email": "example1@example.com",
      "name": "John Doe",
      "phone": "+1234567890",
      "address_city": "Tokyo",
      "address_country": "Japan",
      "created": "2023/01/01 09:00:00"
    },
    {
      "cus_id": "cus_0987654321",
      "email": "example2@example.com",
      "name": "Jane Smith",
      "phone": "+0987654321",
      "address_city": "Osaka",
      "address_country": "Japan",
      "created": "2023/02/01 10:00:00"
    }
  ]
}
```

---

### 2. サブスクリプション情報の検索

#### URL

```
GET /search_subscriptions
```

#### パラメータ

- `api_key` (必須): StripeのAPIキー。  
- `cus_ids` (オプション): カンマ区切りの顧客ID。指定がない場合、デフォルトで`"cus_PCvnk7s61noGQW"`が使用されます。

#### 機能説明

指定された顧客IDに関連するサブスクリプション情報を取得します。複数の顧客IDを指定可能です。

#### リクエスト例

```bash
curl -X GET "http://127.0.0.1:8000/search_subscriptions?api_key=sk_test_4eC39HqLyjWDarjtT1zdp7dc&cus_ids=cus_1234567890,cus_0987654321"
```

#### レスポンス例

```json
{
  "records": [
    {
      "sub_id": "sub_abcdefg12345",
      "customer": "cus_1234567890",
      "status": "active",
      "current_period_start": "2024/09/18 00:00:00",
      "current_period_end": "2024/10/18 00:00:00",
      "plan_amount": 5000,
      "plan_currency": "jpy",
      "plan_interval": "month",
      "subscription_item_names": "BasicPlan AdditionalPlan"
    },
    {
      "sub_id": "sub_hijklmn67890",
      "customer": "cus_0987654321",
      "status": "canceled",
      "current_period_start": "2023/08/01 00:00:00",
      "current_period_end": "2023/09/01 00:00:00",
      "plan_amount": 3000,
      "plan_currency": "jpy",
      "plan_interval": "month",
      "subscription_item_names": "BasicPlan"
    }
  ]
}
```

---

### 3. サブスクリプションアイテム情報の検索

#### URL

```
GET /search_subscription_items
```

#### パラメータ

- `api_key` (必須): StripeのAPIキー。  
- `subscription_ids` (オプション): カンマ区切りのサブスクリプションID。指定がない場合、デフォルトで`"sub_1OOVw0APdno01lSPQNcrQCSC"`が使用されます。

#### 機能説明

指定されたサブスクリプションIDに関連するサブスクリプションアイテムと、そのアイテムに関連するプロダクト情報を取得します。

#### リクエスト例

```bash
curl -X GET "http://127.0.0.1:8000/search_subscription_items?api_key=sk_test_4eC39HqLyjWDarjtT1zdp7dc&subscription_ids=sub_abcdefg12345,sub_hijklmn67890"
```

#### レスポンス例

```json
{
  "records": [
    {
      "si_id": "si_1234567890",
      "subscription": "sub_abcdefg12345",
      "price_product": "prod_1234567890",
      "product_prod_id": "prod_1234567890",
      "product_name": "Premium Plan",
      "price_amount": 5000,
      "currency": "jpy",
      "product_description": "Access to premium features",
      "product_active": true
    },
    {
      "si_id": "si_0987654321",
      "subscription": "sub_hijklmn67890",
      "price_product": "prod_0987654321",
      "product_prod_id": "prod_0987654321",
      "product_name": "Basic Plan",
      "price_amount": 3000,
      "currency": "jpy",
      "product_description": "Access to basic features",
      "product_active": true
    }
  ]
}
```

---

### 4. 請求情報の検索

#### URL

```
GET /search_charges_by_subscription
```

#### パラメータ

- `api_key` (必須): StripeのAPIキー。  
- `subscription_ids` (オプション): カンマ区切りのサブスクリプションID。指定がない場合、デフォルトで`"sub_1OOVw0APdno01lSPQNcrQCSC"`が使用されます。

#### 機能説明

指定されたサブスクリプションIDに関連する請求情報（Charges）を取得します。  
レスポンス内で `ch_id` が請求（Charge）のIDであり、`inv_id` がインボイスのIDになります。

#### リクエスト例

```bash
curl -X GET "http://127.0.0.1:8000/search_charges_by_subscription?api_key=sk_test_4eC39HqLyjWDarjtT1zdp7dc&subscription_ids=sub_abcdefg12345,sub_hijklmn67890"
```

#### レスポンス例

```json
{
  "records": [
    {
      "ch_id": "ch_1234567890",
      "amount": 5000,
      "currency": "jpy",
      "customer": "cus_1234567890",
      "description": "Subscription charge",
      "invoice": "inv_1234567890",
      "paid": true,
      "status": "succeeded",
      "created": "2023/05/01 10:00:00"
    },
    {
      "ch_id": "ch_0987654321",
      "amount": 3000,
      "currency": "jpy",
      "customer": "cus_0987654321",
      "description": "Subscription charge",
      "invoice": "inv_0987654321",
      "paid": true,
      "status": "succeeded",
      "created": "2023/06/01 11:00:00"
    }
  ]
}
```

---

### 5. インボイス情報の検索

#### URL

```
GET /search_invoices_by_subscription
```

#### パラメータ

- `api_key` (必須): StripeのAPIキー。  
- `subscription_ids` (オプション): カンマ区切りのサブスクリプションID。指定がない場合、デフォルトで`"sub_1OOVw0APdno01lSPQNcrQCSC"`が使用されます。

#### 機能説明

指定されたサブスクリプションIDに関連するインボイス情報を取得します。レスポンス内で `inv_id` がインボイスIDとして出力されます。

#### リクエスト例

```bash
curl -X GET "http://127.0.0.1:8000/search_invoices_by_subscription?api_key=sk_test_4eC39HqLyjWDarjtT1zdp7dc&subscription_ids=sub_abcdefg12345,sub_hijklmn67890"
```

#### レスポンス例

```json
{
  "records": [
    {
      "inv_id": "in_1234567890",
      "customer": "cus_1234567890",
      "subscription": "sub_abcdefg12345",
      "status": "paid",
      "total": 5000,
      "currency": "jpy",
      "created": "2023/05/01 09:55:00",
      "period_start": "2023/05/01 00:00:00",
      "period_end": "2023/06/01 00:00:00"
    },
    {
      "inv_id": "in_0987654321",
      "customer": "cus_0987654321",
      "subscription": "sub_hijklmn67890",
      "status": "paid",
      "total": 3000,
      "currency": "jpy",
      "created": "2023/06/01 10:55:00",
      "period_start": "2023/06/01 00:00:00",
      "period_end": "2023/07/01 00:00:00"
    }
  ]
}
```

---

### 6. 請求IDからインボイス情報の検索

#### URL

```
GET /search_invoice_by_charge
```

#### パラメータ

- `api_key` (必須): StripeのAPIキー。  
- `charge_ids` (オプション): カンマ区切りの請求ID。指定がない場合、例として `"ch_3QPcaNAPdno01lSP0ZhfiKYJ"` などがデフォルトで使用されます。

#### 機能説明

指定された請求IDに関連するインボイス情報を取得します。こちらもインボイスのIDは `inv_id`、請求のIDは `ch_id` で返却されます。

#### リクエスト例

```bash
curl -X GET "http://127.0.0.1:8000/search_invoice_by_charge?api_key=sk_test_4eC39HqLyjWDarjtT1zdp7dc&charge_ids=ch_1234567890,ch_0987654321"
```

#### レスポンス例

```json
{
  "records": [
    {
      "inv_id": "in_1234567890",
      "charge": "ch_1234567890",
      "customer": "cus_1234567890",
      "subscription": "sub_abcdefg12345",
      "status": "paid",
      "total": 5000,
      "currency": "jpy",
      "created": "2023/05/01 09:55:00",
      "period_start": "2023/05/01 00:00:00",
      "period_end": "2023/06/01 00:00:00",
      "lines_0_description": "Monthly subscription fee",
      "lines_0_amount": 5000,
      "lines_0_currency": "jpy"
    },
    {
      "inv_id": "in_0987654321",
      "charge": "ch_0987654321",
      "customer": "cus_0987654321",
      "subscription": "sub_hijklmn67890",
      "status": "paid",
      "total": 3000,
      "currency": "jpy",
      "created": "2023/06/01 10:55:00",
      "period_start": "2023/06/01 00:00:00",
      "period_end": "2023/07/01 00:00:00",
      "lines_0_description": "Monthly subscription fee",
      "lines_0_amount": 3000,
      "lines_0_currency": "jpy"
    }
  ]
}
```

---

### 7. サブスクリプションIDからサブスクリプション情報の直接検索

#### URL

```
GET /search_subscriptions_by_id
```

#### パラメータ

- `api_key` (必須): StripeのAPIキー。  
- `subscription_ids` (オプション): カンマ区切りのサブスクリプションID。指定がない場合、デフォルトで`"sub_1OOVw0APdno01lSPQNcrQCSC"`が使用されます。

#### 機能説明

1つまたは複数のサブスクリプションIDを直接指定し、それぞれのサブスクリプション情報を検索します。取得したサブスクリプション情報は**フラット化**されるとともに、`id`が`sub_id`に置き換わります。

#### リクエスト例

```bash
curl -X GET "http://127.0.0.1:8000/search_subscriptions_by_id?api_key=sk_test_4eC39HqLyjWDarjtT1zdp7dc&subscription_ids=sub_abcdefg12345,sub_hijklmn67890"
```

#### レスポンス例

```json
{
  "records": [
    {
      "sub_id": "sub_abcdefg12345",
      "object": "subscription",
      "customer": "cus_1234567890",
      "status": "active",
      "current_period_start": "2024/09/18 00:00:00",
      "current_period_end": "2024/10/18 00:00:00",
      ...
    },
    {
      "sub_id": "sub_hijklmn67890",
      "object": "subscription",
      "customer": "cus_0987654321",
      "status": "canceled",
      "current_period_start": "2023/08/01 00:00:00",
      "current_period_end": "2023/09/01 00:00:00",
      ...
    }
  ]
}
```

---

### 8. フルデータ検索 (search_subscriptions_fulldata)

#### URL

```
GET /search_subscriptions_fulldata
```

#### パラメータ

- `api_key` (必須): StripeのAPIキー。  
- `cus_ids` (オプション): カンマ区切りの顧客ID。指定がない場合、デフォルトで`"cus_PCvnk7s61noGQW"`が使用されます。

#### 機能説明

顧客IDからサブスクリプション全情報を取得し、  
- **SubscriptionItemごとの商品名や価格情報**  
- **次回請求 (upcoming invoice) のプレビュー**  
- **これまでのインボイス情報**  
- **月額合計や簡易的な消費税10%計算**  

などを**まとめて返却**します。レスポンス内では、サブスクリプションの各Itemsを `items_expanded` として持ち、そこに商品名や価格などの詳細が含まれます。

#### リクエスト例

```bash
curl -X GET "http://127.0.0.1:8000/search_subscriptions_fulldata?api_key=sk_test_4eC39HqLyjWDarjtT1zdp7dc&cus_ids=cus_1234567890,cus_0987654321"
```

#### レスポンス例（抜粋）

```json
{
  "records": [
    {
      "sub_id": "sub_abcdefg12345",
      "customer": "cus_1234567890",
      "status": "active",
      "items_expanded": [
        {
          "si_id": "si_XXXXX",
          "product_name": "Test Subscription Product 01",
          "price_nickname": null,
          "price_unit_amount": 100,
          "price_currency": "jpy",
          "quantity": 2
        },
        {
          "si_id": "si_YYYYY",
          "product_name": "Test Subscription Product 02",
          "price_nickname": null,
          "price_unit_amount": 33,
          "price_currency": "jpy",
          "quantity": 1
        }
      ],
      "invoices": [
        {
          "inv_id": "in_XXXXXXX",
          "status": "paid",
          "amount_paid": 200,
          "amount_due": 200,
          "currency": "jpy",
          "created_at": "2024/12/26 11:59:00"
        },
        ...
      ],
      "next_invoice_preview": {
        "amount_due": 133,
        "currency": "jpy",
        "next_invoice_date": "2025/01/26 00:00:00",
        "lines": [
          {
            "description": null,
            "amount": 133,
            "quantity": 1,
            "price_id": "price_1OOVBYAPdno01lSP1B9oRb05"
          }
        ]
      },
      "calculated_monthly_total": 133,
      "calculated_monthly_tax": 13,
      "calculated_monthly_grand_total": 146
    }
  ]
}
```

- `calculated_monthly_total`: サブスクリプションアイテムの小計（例：税抜き）
- `calculated_monthly_tax`: 仮で10%を掛け合わせた消費税（StripeのTax機能とは別の参考値）
- `calculated_monthly_grand_total`: 小計と消費税の合計
- `invoices`: これまでに発行されたインボイス一覧  
- `next_invoice_preview`: 次回請求予定があれば、そのプレビュー

---

## インストール方法

### 前提条件

- **Python 3.7**以上  
- **pip**

### 手順

1. **リポジトリのクローン**

   ```bash
   git clone https://github.com/yourusername/your-repo-name.git
   cd your-repo-name
   ```

2. **仮想環境の作成とアクティベート**

   ```bash
   python -m venv venv
   source venv/bin/activate  # Windowsの場合: venv\Scripts\activate
   ```

3. **依存関係のインストール**

   ```bash
   pip install -r requirements.txt
   ```

   **主な依存関係**
   - `fastapi`
   - `uvicorn`
   - `stripe`
   - `pydantic`
   - `mangum`
   - `pytest`（テスト用）
   - `pytest-cov`（テストカバレッジ用）

## 環境設定

### 環境変数の設定

- **Stripe APIキーの管理**：APIキーは各エンドポイントのクエリパラメータとして渡しますが、セキュリティ上の観点から環境変数として設定することを推奨します。

  ```bash
  export STRIPE_API_KEY=sk_test_4eC39HqLyjWDarjtT1zdp7dc
  ```

  または`.env`ファイルを作成し、次のように記述します。

  ```
  STRIPE_API_KEY=sk_test_4eC39HqLyjWDarjtT1zdp7dc
  ```

- **タイムゾーンの設定**：デフォルトではJST（日本標準時）に設定されています。必要に応じてコード内の`timezone`設定を変更してください。

## 使用方法

### ローカルでの実行

```bash
uvicorn main:app --reload
```

### APIドキュメントの閲覧

ブラウザで `http://127.0.0.1:8000/docs` にアクセスすると、Swagger UIでAPIドキュメントを確認できます。

### エンドポイントの呼び出し

上記の[エンドポイント詳細](#エンドポイント詳細)セクションを参照し、必要なパラメータを指定してAPIを呼び出します。

## リクエストとレスポンスの例

各エンドポイントのリクエストとレスポンスの例は、[エンドポイント詳細](#エンドポイント詳細)セクションで確認できます。  
**特に`id`はすべて`???_id`にリネームされている点を、開発者の方はご注意ください。**

## エラーハンドリング

- **バリデーションエラー (422 Unprocessable Entity)**：入力パラメータが不正な場合に発生します。  
- **認証エラー (401 Unauthorized)**：無効なAPIキーが提供された場合に発生する可能性があります。  
- **サーバーエラー (500 Internal Server Error)**：予期しないエラーが発生した場合に発生します。  
- **Stripe APIエラー (400 Bad Request)**：Stripe APIからのエラーが発生した場合に発生します。

**エラーレスポンスの例**

```json
{
  "detail": "Validation error: ..."
}
```

## テスト方法

### 単体テストの実行

テストには`pytest`を使用しています。以下のコマンドでテストを実行できます。

```bash
pytest tests/
```

### テストカバレッジの確認

```bash
pytest --cov=./
```

`tests/`ディレクトリには各エンドポイントおよびユーティリティ関数のテストケースが含まれています。

## デプロイ方法（AWS Lambda）

### 前提条件

- **AWS CLI**がインストールされ、設定されていること  
- **SAM CLI**がインストールされていること

### 手順

1. **AWS CLIの設定**

   ```bash
   aws configure
   ```

2. **SAM CLIのインストール**

   ```bash
   pip install aws-sam-cli
   ```

3. **テンプレートファイルの作成**

   `template.yaml` ファイルを作成し、以下のように記述します。

   ```yaml
   AWSTemplateFormatVersion: '2010-09-09'
   Transform: AWS::Serverless-2016-10-31
   Description: Stripe API Proxy

   Resources:
     StripeApiFunction:
       Type: AWS::Serverless::Function
       Properties:
         CodeUri: .
         Handler: main.handler
         Runtime: python3.8
         Events:
           ApiEvent:
             Type: Api
             Properties:
               Path: /{proxy+}
               Method: ANY
   ```

4. **ビルドとデプロイ**

   ```bash
   sam build
   sam deploy --guided
   ```

   プロンプトに従い、スタック名、リージョン、パラメータなどを設定します。

5. **デプロイ後の確認**

   デプロイが完了すると、APIエンドポイントのURLが表示されます。ブラウザまたはツールを使用してAPIにアクセスできます。

## セキュリティと認証

- **APIキーの安全な管理**：APIキーは環境変数やAWS Secrets Managerなどで安全に管理してください。  
- **HTTPSの使用**：通信を暗号化するためにHTTPSを使用してください。  
- **入力検証**：Pydanticを使用して入力パラメータを厳格に検証していますが、追加のセキュリティ対策も検討してください。

## ログとモニタリング

- **ロギング**：Pythonの`logging`モジュールを使用してINFOレベルのログを出力しています。エラー時にはERRORレベルのログが記録されます。  
- **モニタリング**：AWS CloudWatchなどのモニタリングサービスを使用して、Lambda関数のパフォーマンスとログを監視することを推奨します。

## 制限事項と考慮点

- **レート制限**：Stripe APIのレート制限に注意してください。一度に大量のリクエストを送信しないよう、適切な間隔を設けてください。  
- **データの整合性**：取得したデータが最新であることを保証するため、キャッシュを適切に管理してください。  
- **タイムゾーン**：日時情報はJSTに変換されていますが、他のタイムゾーンが必要な場合はコードを調整してください。  
- **IDリネーム時の参照**：Stripeオブジェクトの`id`を参照するコードを組む際、`???_id`に変換されている点に注意してください。

## 貢献方法

1. **リポジトリをフォーク**します。  
2. **新しいブランチを作成**します。  

   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **変更をコミット**します。  

   ```bash
   git commit -m "Add your message"
   ```

4. **リモートリポジトリにプッシュ**します。  

   ```bash
   git push origin feature/your-feature-name
   ```

5. **プルリクエストを作成**します。  

## ライセンス

このプロジェクトは[MITライセンス](LICENSE)の下で公開されています。

## 注意事項

- **Stripeの利用規約遵守**：このAPIを使用する際は、Stripeの利用規約とデータ保護ポリシーを遵守してください。  
- **十分なテスト**：本番環境で使用する前に、十分なテストを行ってください。  
- **APIキーの管理**：APIキーは安全に管理し、公開リポジトリにコミットしないよう注意してください。

## FAQ

### Q1: タイムアウトエラーが発生します。

**A1**: ネットワーク環境やStripe APIの応答時間によってはタイムアウトが発生する可能性があります。リトライ機能の実装やタイムアウト設定の見直しを検討してください。

### Q2: 大量のデータを一度に取得するとエラーになります。

**A2**: Stripe APIにはリクエストサイズの制限があります。データを分割して取得するか、ページネーションを実装してください。

### Q3: エラーメッセージが英語で表示されます。

**A3**: 現在、エラーメッセージは英語で提供されています。必要に応じて国際化対応を行ってください。

## お問い合わせ

ご質問やご提案がございましたら、以下の方法でご連絡ください。

- **Issue Tracker**: [GitHub Issues](https://github.com/yourusername/your-repo-name/issues)  
- **プルリクエスト**: ご提案やバグ修正はプルリクエストとして提出してください。  

---
