from fastapi import FastAPI, HTTPException, Query
from typing import List, Optional
import stripe
import logging
from pydantic import BaseModel, EmailStr, ValidationError
from mangum import Mangum  # Mangumのインポート

# ロギング設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Pydanticで入力バリデーションのクラスを作成
class SearchRequest(BaseModel):
    api_key: str
    email_addresses: List[EmailStr]  # EmailStrでメールアドレスの形式を検証

class SubscriptionSearchRequest(BaseModel):
    api_key: str
    cus_ids: List[str]  # 複数の顧客IDを受け取る

def flatten_dict(data: dict, parent_key: str = '', sep: str = '_'):
    """
    ネストされた辞書を平坦化する関数
    """
    items = []
    for k, v in data.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        elif isinstance(v, list):
            # リストの場合はカンマ区切りで文字列に変換
            items.append((new_key, ', '.join(map(str, v)) if v else None))
        else:
            items.append((new_key, v))
    return dict(items)

def search_customers_by_email(api_key: str, email_addresses: List[str]):
    # StripeのAPIキーを設定
    stripe.api_key = api_key

    results = []  # すべての結果をリストでまとめる

    for email in email_addresses:
        try:
            # Stripe APIの顧客検索を行う
            customers = stripe.Customer.list(email=email).data
        except stripe.error.StripeError as e:
            logger.error(f"Stripe API error for email {email}: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Stripe API error for {email}: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error during search for {email}: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Unexpected error during search for {email}: {str(e)}")

        # 顧客IDを "id" から "cus_id" に変更し、ネストを平坦化
        for customer in customers:
            customer_dict = customer.to_dict()  # Stripeオブジェクトを辞書に変換
            customer_dict['cus_id'] = customer_dict.pop('id')  # "id"を"cus_id"に変更

            # ネストされた辞書を平坦化
            flat_customer = flatten_dict(customer_dict)
            results.append(flat_customer)  # 各顧客情報をリストに追加

    return {"records": results}  # リスト全体を "records" キーに含める

def search_subscriptions_by_customer_ids(api_key: str, cus_ids: List[str]):
    # StripeのAPIキーを設定
    stripe.api_key = api_key

    results = []  # すべての結果をリストでまとめる

    for cus_id in cus_ids:
        try:
            # Stripe APIのサブスクリプション検索を行う
            subscriptions = stripe.Subscription.list(customer=cus_id).data
        except stripe.error.StripeError as e:
            logger.error(f"Stripe API error for customer ID {cus_id}: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Stripe API error for customer ID {cus_id}: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error during search for customer ID {cus_id}: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Unexpected error during search for customer ID {cus_id}: {str(e)}")

        # ネストを平坦化
        for subscription in subscriptions:
            subscription_dict = subscription.to_dict()  # Stripeオブジェクトを辞書に変換
            flat_subscription = flatten_dict(subscription_dict)
            results.append(flat_subscription)  # 各サブスクリプション情報をリストに追加

    return {"records": results}  # リスト全体を "records" キーに含める

@app.get("/search_customers")
def get_customers(api_key: str = Query(..., description="Stripe API key"),
                  email_addresses: Optional[str] = Query(None, description="Comma separated list of email addresses")):
    try:
        # email_addressesが指定されていない場合、デフォルトで "hori@revol.co.jp" を使用
        if email_addresses is None or email_addresses.strip() == "":
            email_list = ["hori@revol.co.jp"]
        else:
            # メールアドレスをカンマで区切ってリストに変換
            email_list = [email.strip() for email in email_addresses.split(',')]

        # EmailStrを使って各メールアドレスのバリデーションを実施
        validated_request = SearchRequest(api_key=api_key, email_addresses=email_list)

        # Stripe APIを使用して顧客情報を取得
        customers = search_customers_by_email(validated_request.api_key, validated_request.email_addresses)

        # JSONの形式を "records" 配列の中に入れる
        return customers
    except ValidationError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(status_code=422, detail=f"Validation error: {str(e)}")
    except HTTPException as e:
        raise e  # 既に処理されたHTTP例外はそのまま伝播させる
    except Exception as e:
        logger.error(f"Unexpected server error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error. Please try again later.")

@app.get("/search_subscriptions")
def get_subscriptions(api_key: str = Query(..., description="Stripe API key"),
                      cus_ids: Optional[str] = Query(None, description="Comma separated list of customer IDs")):
    try:
        # cus_idsが指定されていない場合、デフォルトで "cus_PCvnk7s61noGQW" を使用
        if cus_ids is None or cus_ids.strip() == "":
            cus_id_list = ["cus_PCvnk7s61noGQW"]
        else:
            # カンマ区切りのcus_idsをリストに変換
            cus_id_list = [cus_id.strip() for cus_id in cus_ids.split(',')]

        # cus_ids のバリデーションを実施
        validated_request = SubscriptionSearchRequest(api_key=api_key, cus_ids=cus_id_list)

        # Stripe APIを使用してサブスクリプション情報を取得
        subscriptions = search_subscriptions_by_customer_ids(validated_request.api_key, validated_request.cus_ids)

        # JSONの形式を "records" 配列の中に入れる
        return subscriptions
    except ValidationError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(status_code=422, detail=f"Validation error: {str(e)}")
    except HTTPException as e:
        raise e  # 既に処理されたHTTP例外はそのまま伝播させる
    except Exception as e:
        logger.error(f"Unexpected server error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error. Please try again later.")

# Lambda用のハンドラー
handler = Mangum(app)
