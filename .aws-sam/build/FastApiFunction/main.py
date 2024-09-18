from fastapi import FastAPI, HTTPException, Query
from typing import List
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

        # 顧客IDを "id" から "cus_id" に変更
        for customer in customers:
            customer_dict = customer.to_dict()  # Stripeオブジェクトを辞書に変換
            customer_dict['cus_id'] = customer_dict.pop('id')  # "id"を"cus_id"に変更
            results.append(customer_dict)  # 各顧客情報をリストに追加

    return results  # リスト全体を返す

@app.get("/search_customers")
def get_customers(api_key: str = Query(..., description="Stripe API key"),
                  email_addresses: str = Query(..., description="Comma separated list of email addresses")):
    try:
        # メールアドレスをカンマで区切ってリストに変換
        email_list = [email.strip() for email in email_addresses.split(',')]

        # EmailStrを使って各メールアドレスのバリデーションを実施
        validated_request = SearchRequest(api_key=api_key, email_addresses=email_list)

        # Stripe APIを使用して顧客情報を取得
        customers = search_customers_by_email(validated_request.api_key, validated_request.email_addresses)
        return customers
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

