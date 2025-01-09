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

class SubscriptionDirectSearchRequest(BaseModel):
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


def rename_id_field(obj_dict: dict, object_type: str) -> dict:
    """
    受け取った dict の "id" を、object_type + "_id" にリネームする補助関数。
    object_type が 'customer' → 'cus_id', 'subscription' → 'sub_id' などのように変換。
    """
    if "id" in obj_dict:
        new_key = ""
        if object_type == "customer":
            new_key = "cus_id"
        elif object_type == "subscription":
            new_key = "sub_id"
        elif object_type == "subscription_item":
            new_key = "si_id"
        elif object_type == "invoice":
            new_key = "inv_id"
        elif object_type == "charge":
            new_key = "ch_id"
        elif object_type == "product":
            new_key = "prod_id"
        elif object_type == "price":
            new_key = "price_id"
        elif object_type == "plan":
            new_key = "plan_id"
        else:
            # 該当しない場合は "_id" としておく
            new_key = f"{object_type}_id"

        # pop して rename
        obj_dict[new_key] = obj_dict.pop("id")
    return obj_dict

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
            if new_key in [
                'billing_cycle_anchor', 'created', 'current_period_end',
                'current_period_start', 'start_date', 'trial_end', 'trial_start'
            ]:
                # UNIXタイムスタンプをJSTに変換
                v = datetime.fromtimestamp(v, tz=timezone.utc).astimezone(JST).strftime('%Y/%m/%d %H:%M:%S')
            items.append((new_key, v))
    return dict(items)


# サブスクリプションIDでItemsデータを1階層だけフラット化し、関連するプロダクト情報も取得
def search_subscription_items_by_id(api_key: str, subscription_ids: List[str]):
    stripe.api_key = api_key
    results = []

    for subscription_id in subscription_ids:
        try:
            # 単一サブスクリプションを直接retrieve
            subscription = stripe.Subscription.retrieve(subscription_id)
            subscription_dict = rename_id_field(subscription.to_dict(), "subscription")

            # items.data の要素を処理
            for item in subscription_dict['items']['data']:
                item_dict = rename_id_field(item, "subscription_item")

                # price から product を取得
                price_product_id = item_dict.get("price", {}).get("product")
                if price_product_id:
                    try:
                        product_obj = stripe.Product.retrieve(price_product_id)
                        product_dict = rename_id_field(product_obj.to_dict(), "product")
                        # フラット化して item_dict に統合
                        flat_product = flatten_json(product_dict, parent_key='product')
                        item_dict.update(flat_product)
                    except stripe.error.StripeError as e:
                        logger.error(f"Stripe API error for product ID {price_product_id}: {str(e)}")
                        raise HTTPException(status_code=400, detail=f"Stripe API error for product ID {price_product_id}: {str(e)}")
                    except Exception as e:
                        logger.error(f"Unexpected error during search for product ID {price_product_id}: {str(e)}")
                        raise HTTPException(status_code=500, detail=f"Unexpected error during search for product ID {price_product_id}: {str(e)}")

                flat_item = flatten_json(item_dict)
                results.append(flat_item)

        except stripe.error.StripeError as e:
            logger.error(f"Stripe API error for subscription ID {subscription_id}: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Stripe API error for subscription ID {subscription_id}: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error during search for subscription ID {subscription_id}: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Unexpected error during search for subscription ID {subscription_id}: {str(e)}")

    return {"records": results}


# 顧客のメールアドレスで顧客情報を検索
def search_customers_by_email(api_key: str, email_addresses: List[str]):
    stripe.api_key = api_key
    results = []

    for email in email_addresses:
        try:
            # 顧客を検索 (listオブジェクト)
            customers_response = stripe.Customer.list(email=email)
            # auto_paging_iter() または .data いずれかでループ可
            for customer in customers_response.auto_paging_iter():
                customer_dict = rename_id_field(customer.to_dict(), "customer")
                flat_customer = flatten_json(customer_dict)
                results.append(flat_customer)

        except stripe.error.StripeError as e:
            logger.error(f"Stripe API error for email {email}: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Stripe API error for {email}: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error during search for {email}: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Unexpected error during search for {email}: {str(e)}")

    return {"records": results}


# 顧客IDでサブスクリプション情報を検索
def search_subscriptions_by_customer_ids(api_key: str, cus_ids: List[str]):
    stripe.api_key = api_key
    results = []

    for cus_id in cus_ids:
        try:
            # サブスクリプションを取得 (listオブジェクト)
            subs_response = stripe.Subscription.list(customer=cus_id)
            # auto_paging_iter でループしながら取得
            for subscription in subs_response.auto_paging_iter():
                subscription_dict = rename_id_field(subscription.to_dict(), "subscription")

                # item_names (例) を作る
                item_names = []
                for item in subscription.items.data:
                    product_id = item["price"]["product"]
                    try:
                        product_obj = stripe.Product.retrieve(product_id)
                        item_names.append(product_obj["name"])
                    except stripe.error.StripeError as e:
                        logger.error(f"Stripe API error for product ID {product_id}: {str(e)}")
                        raise HTTPException(status_code=400, detail=f"Stripe API error for product ID {product_id}: {str(e)}")
                    except Exception as e:
                        logger.error(f"Unexpected error during search for product ID {product_id}: {str(e)}")
                        raise HTTPException(status_code=500, detail=f"Unexpected error during search for product ID {product_id}: {str(e)}")

                subscription_dict["subscription_item_names"] = " ".join(item_names)
                flat_subscription = flatten_json(subscription_dict)
                results.append(flat_subscription)

        except stripe.error.StripeError as e:
            logger.error(f"Stripe API error for customer ID {cus_id}: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Stripe API error for customer ID {cus_id}: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error during search for customer ID {cus_id}: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Unexpected error during search for customer ID {cus_id}: {str(e)}")

    return {"records": results}


# サブスクリプションIDからサブスクリプション情報を検索
def search_subscriptions_by_ids(api_key: str, subscription_ids: List[str]):
    stripe.api_key = api_key
    results = []
    for sub_id in subscription_ids:
        try:
            subscription = stripe.Subscription.retrieve(sub_id)
            subscription_dict = rename_id_field(subscription.to_dict(), "subscription")
            flat_subscription = flatten_json(subscription_dict)
            results.append(flat_subscription)
        except stripe.error.StripeError as e:
            logger.error(f"Stripe API error for subscription ID {sub_id}: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Stripe API error for subscription ID {sub_id}: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error during search for subscription ID {sub_id}: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Unexpected error during search for subscription ID {sub_id}: {str(e)}")
    return {"records": results}


# サブスクリプションIDに連なる請求(Charge)を取得
def search_charges_by_subscription(api_key: str, subscription_ids: List[str]):
    stripe.api_key = api_key
    results = []
    for subscription_id in subscription_ids:
        try:
            invoices = stripe.Invoice.list(subscription=subscription_id)
            for inv in invoices.auto_paging_iter():
                inv_dict = rename_id_field(inv.to_dict(), "invoice")
                charges = stripe.Charge.list(invoice=inv_dict.get("inv_id"))

                # chargesも listオブジェクト
                for ch in charges.auto_paging_iter():
                    charge_dict = rename_id_field(ch.to_dict(), "charge")
                    flat_charge = flatten_json(charge_dict)
                    results.append(flat_charge)

        except stripe.error.StripeError as e:
            logger.error(f"Stripe API error for subscription ID {subscription_id}: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Stripe API error for subscription ID {subscription_id}: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error during search for subscription ID {subscription_id}: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Unexpected error during search for subscription ID {subscription_id}: {str(e)}")

    return {"records": results}


# サブスクリプションIDに連なるインボイスを取得
def get_invoices_by_subscription_id(api_key: str, subscription_ids: List[str]):
    stripe.api_key = api_key
    results = []
    for subscription_id in subscription_ids:
        try:
            invoices = stripe.Invoice.list(subscription=subscription_id)
            for inv in invoices.auto_paging_iter():
                inv_dict = rename_id_field(inv.to_dict(), "invoice")
                flattened_invoices = flatten_json(inv_dict)
                results.append(flattened_invoices)
        except stripe.error.StripeError as e:
            logger.error(f"Stripe API error for subscription ID {subscription_id}: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Stripe API error for subscription ID {subscription_id}: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error during search for subscription ID {subscription_id}: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Unexpected error during search for subscription ID {subscription_id}: {str(e)}")
    return {"records": results}


# 請求IDに連なるインボイスを取得
def get_invoice_by_charge_id(api_key: str, charge_ids: List[str]):
    stripe.api_key = api_key
    results = []
    for charge_id in charge_ids:
        try:
            charge_obj = stripe.Charge.retrieve(charge_id)
            charge_dict = rename_id_field(charge_obj.to_dict(), "charge")

            if 'invoice' in charge_dict:
                invoice_id = charge_dict['invoice']
                invoice_obj = stripe.Invoice.retrieve(invoice_id)
                inv_dict = rename_id_field(invoice_obj.to_dict(), "invoice")
                flattened_invoice = flatten_json(inv_dict)
                results.append(flattened_invoice)

        except stripe.error.StripeError as e:
            logger.error(f"Stripe API error for charge ID {charge_id}: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Stripe API error for charge ID {charge_id}: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error during search for charge ID {charge_id}: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Unexpected error during search for charge ID {charge_id}: {str(e)}")
    return {"records": results}


# ============ FastAPIのエンドポイント定義 ============

@app.get("/search_customers")
def get_customers(
    api_key: str = Query(..., description="Stripe API key"),
    email_addresses: Optional[str] = Query(None, description="Comma separated list of email addresses")
):
    try:
        if email_addresses is None or email_addresses.strip() == "":
            email_list = ["hori@revol.co.jp"]
        else:
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
def get_subscriptions(
    api_key: str = Query(..., description="Stripe API key"),
    cus_ids: Optional[str] = Query(None, description="Comma separated list of customer IDs")
):
    try:
        if cus_ids is None or cus_ids.strip() == "":
            cus_id_list = ["cus_PCvnk7s61noGQW"]
        else:
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


def search_subscriptions_fulldata_by_customer_ids(api_key: str, cus_ids: List[str]):
    """
    顧客IDからサブスクリプションを取得し、以下の追加情報を取得して返す:
      - 各SubscriptionItem の Product名, Price名 等
      - 次回のインボイス (upcoming invoice)
      - これまで発行されたインボイス一覧
      - 必要に応じて計算（例: 税額など）
    """
    stripe.api_key = api_key
    results = []

    for cus_id in cus_ids:
        try:
            # 全サブスクリプション
            subs_response = stripe.Subscription.list(customer=cus_id)
            for subscription in subs_response.auto_paging_iter():
                subscription_dict = rename_id_field(subscription.to_dict(), "subscription")

                # SubscriptionItemごとに詳細取得
                items_expanded = []
                for item in subscription.items.data:
                    item_dict = rename_id_field(item.to_dict(), "subscription_item")

                    price_id = item_dict.get("price", {}).get("id")
                    product_id = item_dict.get("price", {}).get("product")

                    if product_id:
                        try:
                            product_obj = stripe.Product.retrieve(product_id)
                            product_dict = rename_id_field(product_obj.to_dict(), "product")
                            item_dict["product_name"] = product_dict.get("name", "Unnamed Product")
                        except Exception as e:
                            logger.error(f"Error retrieving product {product_id}: {str(e)}")
                            item_dict["product_name"] = f"Error retrieving product {product_id}"

                    if price_id:
                        try:
                            price_obj = stripe.Price.retrieve(price_id)
                            item_dict["price_nickname"] = price_obj.get("nickname")
                            item_dict["price_unit_amount"] = price_obj.get("unit_amount")
                            item_dict["price_currency"] = price_obj.get("currency")
                        except Exception as e:
                            logger.error(f"Error retrieving price {price_id}: {str(e)}")
                            item_dict["price_nickname"] = None

                    items_expanded.append(item_dict)

                subscription_dict["items_expanded"] = items_expanded

                # 次回インボイス(プレビュー)
                try:
                    upcoming_invoice = stripe.Invoice.upcoming(subscription=subscription.id)
                    if upcoming_invoice:
                        subscription_dict["next_invoice_preview"] = {
                            "amount_due": upcoming_invoice.get("amount_due"),
                            "currency": upcoming_invoice.get("currency"),
                            "next_invoice_date": datetime.fromtimestamp(
                                upcoming_invoice.get("due_date", 0), tz=timezone.utc
                            ).astimezone(JST).strftime('%Y/%m/%d %H:%M:%S') if upcoming_invoice.get("due_date") else None,
                            "lines": []
                        }
                        for line in upcoming_invoice.lines:
                            subscription_dict["next_invoice_preview"]["lines"].append({
                                "description": line.get("description"),
                                "amount": line.get("amount"),
                                "quantity": line.get("quantity"),
                                "price_id": line.get("price", {}).get("id"),
                            })
                except stripe.error.InvalidRequestError:
                    subscription_dict["next_invoice_preview"] = None

                # これまでのインボイス
                invoices_data = []
                try:
                    inv_response = stripe.Invoice.list(subscription=subscription.id)
                    for inv in inv_response.auto_paging_iter():
                        inv_dict = rename_id_field(inv.to_dict(), "invoice")
                        invoices_data.append({
                            "inv_id": inv_dict["inv_id"],
                            "status": inv_dict.get("status"),
                            "amount_paid": inv_dict.get("amount_paid"),
                            "amount_due": inv_dict.get("amount_due"),
                            "currency": inv_dict.get("currency"),
                            "created_at": datetime.fromtimestamp(
                                inv.created, tz=timezone.utc
                            ).astimezone(JST).strftime('%Y/%m/%d %H:%M:%S')
                        })
                except Exception as e:
                    logger.error(f"Error retrieving invoices for subscription {subscription.id}: {str(e)}")

                subscription_dict["invoices"] = invoices_data

                # 簡易計算（例: 合計金額+10%税）
                try:
                    monthly_total = 0
                    for item_e in items_expanded:
                        if item_e.get("price_unit_amount") is not None and isinstance(item_e.get("quantity"), int):
                            monthly_total += item_e["price_unit_amount"] * item_e["quantity"]
                    subscription_dict["calculated_monthly_total"] = monthly_total
                    subscription_dict["calculated_monthly_tax"] = int(monthly_total * 0.1)
                    subscription_dict["calculated_monthly_grand_total"] = (
                        subscription_dict["calculated_monthly_total"] 
                        + subscription_dict["calculated_monthly_tax"]
                    )
                except Exception as e:
                    logger.error(f"Error calculating monthly total for subscription {subscription.id}: {str(e)}")
                    subscription_dict["calculated_monthly_total"] = None
                    subscription_dict["calculated_monthly_tax"] = None
                    subscription_dict["calculated_monthly_grand_total"] = None

                results.append(subscription_dict)

        except stripe.error.StripeError as e:
            logger.error(f"Stripe API error for customer ID {cus_id}: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Stripe API error for customer ID {cus_id}: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error during search for customer ID {cus_id}: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Unexpected error during search for customer ID {cus_id}: {str(e)}")

    return {"records": results}


@app.get("/search_subscriptions_fulldata")
def get_subscriptions_fulldata(
    api_key: str = Query(..., description="Stripe API key"),
    cus_ids: Optional[str] = Query(None, description="カンマ区切りの顧客IDリスト")
):
    """
    顧客IDをもとにサブスクリプションを検索し、
    - サブスクリプション情報
    - SubscriptionItemごとの商品名、価格
    - 次回請求書(upcoming invoice)のプレビュー
    - 既存インボイス一覧
    - 必要に応じた計算結果（例: 消費税10% など）
    をまとめて返却する。
    """
    try:
        if not cus_ids or cus_ids.strip() == "":
            cus_id_list = ["cus_PCvnk7s61noGQW"]
        else:
            cus_id_list = [c.strip() for c in cus_ids.split(",")]

        validated_request = SubscriptionSearchRequest(api_key=api_key, cus_ids=cus_id_list)
        return search_subscriptions_fulldata_by_customer_ids(
            validated_request.api_key,
            validated_request.cus_ids
        )

    except ValidationError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(status_code=422, detail=f"Validation error: {str(e)}")
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Unexpected server error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error. Please try again later.")


@app.get("/search_subscription_items")
def get_subscription_items(
    api_key: str = Query(..., description="Stripe API key"),
    subscription_ids: Optional[str] = Query(None, description="Comma separated list of Subscription IDs")
):
    try:
        if subscription_ids is None or subscription_ids.strip() == "":
            subscription_id_list = ["sub_1OOVw0APdno01lSPQNcrQCSC"]
        else:
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


@app.get("/search_subscriptions_by_id")
def get_subscriptions_by_id(
    api_key: str = Query(..., description="Stripe API key"),
    subscription_ids: Optional[str] = Query(None, description="Comma separated list of Subscription IDs")
):
    try:
        if subscription_ids is None or subscription_ids.strip() == "":
            subscription_id_list = ["sub_1OOVw0APdno01lSPQNcrQCSC"]
        else:
            subscription_id_list = [sub_id.strip() for sub_id in subscription_ids.split(',')]

        validated_request = SubscriptionDirectSearchRequest(api_key=api_key, subscription_ids=subscription_id_list)
        subscriptions = search_subscriptions_by_ids(validated_request.api_key, validated_request.subscription_ids)
        return subscriptions
    except ValidationError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(status_code=422, detail=f"Validation error: {str(e)}")
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Unexpected server error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error. Please try again later.")


@app.get("/search_charges_by_subscription")
def get_charges(
    api_key: str = Query(..., description="Stripe API key"),
    subscription_ids: Optional[str] = Query(None, description="Comma separated list of Subscription IDs")
):
    try:
        if subscription_ids is None or subscription_ids.strip() == "":
            subscription_id_list = ["sub_1OOVw0APdno01lSPQNcrQCSC"]
        else:
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


@app.get("/search_invoices_by_subscription")
def get_invoices(
    api_key: str = Query(..., description="Stripe API key"),
    subscription_ids: Optional[str] = Query(None, description="Comma separated list of Subscription IDs")
):
    try:
        if subscription_ids is None or subscription_ids.strip() == "":
            subscription_id_list = ["sub_1OOVw0APdno01lSPQNcrQCSC"]
        else:
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


@app.get("/search_invoice_by_charge")
def get_invoice(
    api_key: str = Query(..., description="Stripe API key"),
    charge_ids: Optional[str] = Query(None, description="Comma separated list of Charge IDs")
):
    try:
        if charge_ids is None or charge_ids.strip() == "":
            charge_id_list = ["ch_3QPcaNAPdno01lSP0ZhfiKYJ"]
        else:
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
