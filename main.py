from fastapi import FastAPI, HTTPException, Query
from typing import List, Optional
import stripe
import logging
from pydantic import BaseModel, EmailStr, ValidationError
from mangum import Mangum  # Mangumのインポート
from datetime import datetime, timezone, timedelta  # タイムゾーン変換用

# ロギング設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# JSTのタイムゾーン設定
JST = timezone(timedelta(hours=9))

# Pydanticで入力バリデーションのクラスを作成
class SearchRequest(BaseModel):
    api_key: str
    email_addresses: List[EmailStr]  # EmailStrでメールアドレスの形式を検証

class SubscriptionSearchRequest(BaseModel):
    api_key: str
    cus_ids: List[str]  # 複数の顧客IDを受け取る

class SubscriptionItemSearchRequest(BaseModel):
    api_key: str
    subscription_ids: List[str]  # 複数のサブスクリプションIDを受け取る

class ChargeSearchRequest(BaseModel):
    api_key: str
    subscription_ids: List[str]  # 複数のサブスクリプションIDを受け取る

class InvoiceSearchRequest(BaseModel):
    api_key: str
    subscription_ids: List[str]  # 複数のサブスクリプションIDを受け取る

class ChargeInvoiceSearchRequest(BaseModel):
    api_key: str
    charge_ids: List[str]  # 複数の請求IDを受け取る

# フラット化のための関数
def flatten_json(nested_json, parent_key='', sep='_'):
    """
    ネストされたJSONをフラット化する再帰的な関数
    """
    items = []
    for k, v in nested_json.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_json(v, new_key, sep=sep).items())
        elif isinstance(v, list):
            for i, item in enumerate(v):
                if isinstance(item, dict):
                    items.extend(flatten_json(item, f"{new_key}_{i}", sep=sep).items())
                else:
                    items.append((f"{new_key}_{i}", item))
        else:
            # UNIXタイムスタンプをJSTに変換する特定のキーをチェック
            if new_key in ['billing_cycle_anchor', 'created', 'current_period_end', 'current_period_start', 'start_date', 'trial_end', 'trial_start']:
                # UNIXタイムスタンプをJSTに変換
                v = datetime.fromtimestamp(v, tz=timezone.utc).astimezone(JST).strftime('%Y/%m/%d %H:%M:%S')
            items.append((new_key, v))
    return dict(items)

# サブスクリプションIDでItemsデータを1階層だけフラット化し、関連するプロダクト情報も取得する関数
def search_subscription_items_by_id(api_key: str, subscription_ids: List[str]):
    # StripeのAPIキーを設定
    stripe.api_key = api_key

    results = []
    for subscription_id in subscription_ids:
        try:
            # サブスクリプションIDでサブスクリプションを検索
            subscription = stripe.Subscription.retrieve(subscription_id)

            # items.data 内の要素を1階層だけフラット化
            for item in subscription['items']['data']:
                flat_item = flatten_json(item)
                
                # price_product（フラット化前はprice.product）の値を使ってプロダクトを取得
                price_product_id = flat_item.get('price_product')
                if price_product_id:
                    try:
                        product = stripe.Product.retrieve(price_product_id)
                        flat_product = flatten_json(product, parent_key='product')  # フラット化
                        # プロダクト情報をflat_itemに追加
                        flat_item.update(flat_product)
                    except stripe.error.StripeError as e:
                        logger.error(f"Stripe API error for product ID {price_product_id}: {str(e)}")
                        raise HTTPException(status_code=400, detail=f"Stripe API error for product ID {price_product_id}: {str(e)}")
                    except Exception as e:
                        logger.error(f"Unexpected error during search for product ID {price_product_id}: {str(e)}")
                        raise HTTPException(status_code=500, detail=f"Unexpected error during search for product ID {price_product_id}: {str(e)}")
                
                results.append(flat_item)

        except stripe.error.StripeError as e:
            logger.error(f"Stripe API error for subscription ID {subscription_id}: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Stripe API error for subscription ID {subscription_id}: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error during search for subscription ID {subscription_id}: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Unexpected error during search for subscription ID {subscription_id}: {str(e)}")

    return {"records": results}  # フラット化されたデータを返す

# 顧客のメールアドレスで顧客情報を検索
def search_customers_by_email(api_key: str, email_addresses: List[str]):
    stripe.api_key = api_key

    results = []

    for email in email_addresses:
        try:
            customers = stripe.Customer.list(email=email).data
        except stripe.error.StripeError as e:
            logger.error(f"Stripe API error for email {email}: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Stripe API error for {email}: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error during search for {email}: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Unexpected error during search for {email}: {str(e)}")

        for customer in customers:
            customer_dict = customer.to_dict()
            customer_dict['cus_id'] = customer_dict.pop('id')
            flat_customer = flatten_json(customer_dict)
            results.append(flat_customer)

    return {"records": results}

# 顧客IDでサブスクリプション情報を検索
def search_subscriptions_by_customer_ids(api_key: str, cus_ids: List[str]):
    stripe.api_key = api_key

    results = []

    for cus_id in cus_ids:
        try:
            subscriptions = stripe.Subscription.list(customer=cus_id).data
        except stripe.error.StripeError as e:
            logger.error(f"Stripe API error for customer ID {cus_id}: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Stripe API error for customer ID {cus_id}: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error during search for customer ID {cus_id}: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Unexpected error during search for customer ID {cus_id}: {str(e)}")

        for subscription in subscriptions:
            flat_subscription = flatten_json(subscription.to_dict())
            results.append(flat_subscription)

    return {"records": results}

# 新しい関数: サブスクリプションIDに連なる請求を取得
def search_charges_by_subscription(api_key: str, subscription_ids: List[str]):
    stripe.api_key = api_key
    results = []

    for subscription_id in subscription_ids:
        try:
            # Step 1: サブスクリプションIDに関連するインボイスを取得
            invoices = stripe.Invoice.list(subscription=subscription_id)

            for invoice in invoices:
                # Step 2: インボイスIDに関連する支払い情報を取得
                charges = stripe.Charge.list(invoice=invoice.id)

                for charge in charges:
                    # Step 3: 支払い情報をフラット化
                    flat_charge = flatten_json(charge)
                    results.append(flat_charge)

        except stripe.error.StripeError as e:
            logger.error(f"Stripe API error for subscription ID {subscription_id}: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Stripe API error for subscription ID {subscription_id}: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error during search for subscription ID {subscription_id}: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Unexpected error during search for subscription ID {subscription_id}: {str(e)}")

    return {"records": results}

# 新しい関数: サブスクリプションIDに連なるインボイスを取得
def get_invoices_by_subscription_id(api_key: str, subscription_ids: List[str]):
    stripe.api_key = api_key
    results = []
    for subscription_id in subscription_ids:
        try:
            invoices = stripe.Invoice.list(subscription=subscription_id)
            flattened_invoices = [flatten_json(invoice) for invoice in invoices.data]
            results.extend(flattened_invoices)
        except stripe.error.StripeError as e:
            logger.error(f"Stripe API error for subscription ID {subscription_id}: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Stripe API error for subscription ID {subscription_id}: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error during search for subscription ID {subscription_id}: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Unexpected error during search for subscription ID {subscription_id}: {str(e)}")
    return {"records": results}

# 新しい関数: 請求IDに連なるインボイスを取得
def get_invoice_by_charge_id(api_key: str, charge_ids: List[str]):
    stripe.api_key = api_key
    results = []
    for charge_id in charge_ids:
        try:
            charge = stripe.Charge.retrieve(charge_id)
            if 'invoice' in charge:
                invoice = stripe.Invoice.retrieve(charge.invoice)
                flattened_invoice = flatten_json(invoice)
                results.append(flattened_invoice)
        except stripe.error.StripeError as e:
            logger.error(f"Stripe API error for charge ID {charge_id}: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Stripe API error for charge ID {charge_id}: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error during search for charge ID {charge_id}: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Unexpected error during search for charge ID {charge_id}: {str(e)}")
    return {"records": results}

@app.get("/search_customers")
def get_customers(api_key: str = Query(..., description="Stripe API key"),
                  email_addresses: Optional[str] = Query(None, description="Comma separated list of email addresses")):
    try:
        # メールアドレスが指定されていない場合、デフォルト値を使用
        if email_addresses is None or email_addresses.strip() == "":
            email_list = ["hori@revol.co.jp"]
        else:
            # カンマ区切りのメールアドレスをリストに変換
            email_list = [email.strip() for email in email_addresses.split(',')]

        validated_request = SearchRequest(api_key=api_key, email_addresses=email_list)
        customers = search_customers_by_email(validated_request.api_key, validated_request.email_addresses)
        return customers
    except ValidationError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(status_code=422, detail=f"Validation error: {str(e)}")
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Unexpected server error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error. Please try again later.")

@app.get("/search_subscriptions")
def get_subscriptions(api_key: str = Query(..., description="Stripe API key"),
                      cus_ids: Optional[str] = Query(None, description="Comma separated list of customer IDs")):
    try:
        # 顧客IDが指定されていない場合、デフォルト値を使用
        if cus_ids is None or cus_ids.strip() == "":
            cus_id_list = ["cus_PCvnk7s61noGQW"]
        else:
            # カンマ区切りの顧客IDをリストに変換
            cus_id_list = [cus_id.strip() for cus_id in cus_ids.split(',')]

        validated_request = SubscriptionSearchRequest(api_key=api_key, cus_ids=cus_id_list)
        subscriptions = search_subscriptions_by_customer_ids(validated_request.api_key, validated_request.cus_ids)
        return subscriptions
    except ValidationError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(status_code=422, detail=f"Validation error: {str(e)}")
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Unexpected server error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error. Please try again later.")

@app.get("/search_subscription_items")
def get_subscription_items(api_key: str = Query(..., description="Stripe API key"),
                           subscription_ids: Optional[str] = Query(None, description="Comma separated list of Subscription IDs")):
    try:
        # subscription_idsが指定されていない場合、デフォルトで 'sub_1OOVw0APdno01lSPQNcrQCSC' を使用
        if subscription_ids is None or subscription_ids.strip() == "":
            subscription_id_list = ["sub_1OOVw0APdno01lSPQNcrQCSC"]
        else:
            # カンマ区切りのsubscription_idsをリストに変換
            subscription_id_list = [sub_id.strip() for sub_id in subscription_ids.split(',')]

        validated_request = SubscriptionItemSearchRequest(api_key=api_key, subscription_ids=subscription_id_list)
        subscription_items = search_subscription_items_by_id(validated_request.api_key, validated_request.subscription_ids)
        return subscription_items
    except ValidationError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(status_code=422, detail=f"Validation error: {str(e)}")
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Unexpected server error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error. Please try again later.")

# 新しいエンドポイント: サブスクリプションIDに連なる請求を取得
@app.get("/search_charges_by_subscription")
def get_charges(api_key: str = Query(..., description="Stripe API key"),
                subscription_ids: Optional[str] = Query(None, description="Comma separated list of Subscription IDs")):
    try:
        # subscription_idsが指定されていない場合、デフォルト値を使用
        if subscription_ids is None or subscription_ids.strip() == "":
            subscription_id_list = ["sub_1OOVw0APdno01lSPQNcrQCSC"]
        else:
            # カンマ区切りのsubscription_idsをリストに変換
            subscription_id_list = [sub_id.strip() for sub_id in subscription_ids.split(',')]

        validated_request = ChargeSearchRequest(api_key=api_key, subscription_ids=subscription_id_list)
        charges = search_charges_by_subscription(validated_request.api_key, validated_request.subscription_ids)
        return charges
    except ValidationError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(status_code=422, detail=f"Validation error: {str(e)}")
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Unexpected server error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error. Please try again later.")

# 新しいエンドポイント: サブスクリプションIDに連なるインボイスを取得
@app.get("/search_invoices_by_subscription")
def get_invoices(api_key: str = Query(..., description="Stripe API key"),
                 subscription_ids: Optional[str] = Query(None, description="Comma separated list of Subscription IDs")):
    try:
        # subscription_idsが指定されていない場合、デフォルト値を使用
        if subscription_ids is None or subscription_ids.strip() == "":
            subscription_id_list = ["sub_1OOVw0APdno01lSPQNcrQCSC"]
        else:
            # カンマ区切りのsubscription_idsをリストに変換
            subscription_id_list = [sub_id.strip() for sub_id in subscription_ids.split(',')]

        validated_request = InvoiceSearchRequest(api_key=api_key, subscription_ids=subscription_id_list)
        invoices = get_invoices_by_subscription_id(validated_request.api_key, validated_request.subscription_ids)
        return invoices
    except ValidationError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(status_code=422, detail=f"Validation error: {str(e)}")
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Unexpected server error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error. Please try again later.")

# 新しいエンドポイント: 請求IDに連なるインボイスを取得
@app.get("/search_invoice_by_charge")
def get_invoice(api_key: str = Query(..., description="Stripe API key"),
                charge_ids: Optional[str] = Query(None, description="Comma separated list of Charge IDs")):
    try:
        # charge_idsが指定されていない場合、エラーを返す
        if charge_ids is None or charge_ids.strip() == "":
            raise HTTPException(status_code=400, detail="Charge ID is required")
        
        # カンマ区切りのcharge_idsをリストに変換
        charge_id_list = [charge_id.strip() for charge_id in charge_ids.split(',')]

        validated_request = ChargeInvoiceSearchRequest(api_key=api_key, charge_ids=charge_id_list)
        invoice = get_invoice_by_charge_id(validated_request.api_key, validated_request.charge_ids)
        return invoice
    except ValidationError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(status_code=422, detail=f"Validation error: {str(e)}")
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Unexpected server error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error. Please try again later.")

# Lambda用のハンドラー
handler = Mangum(app)
