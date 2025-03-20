import logging
import os
from random import choices
import requests

from flask_login import current_user
from werkzeug.exceptions import Forbidden

from controllers.console import api
from flask_restful import Resource, inputs, marshal, reqparse, marshal_with

from controllers.console.app.error import AdNotFoundError
from controllers.console.app.wraps import get_app_model
from controllers.console.wraps import setup_required, account_initialization_required, enterprise_license_required
from extensions.ext_database import db
from fields import advertising_fields
from fields.advertising_fields import advertising_pagination_fields, advertising_detail_fields, \
    advertising_partial_fields
from libs.helper import DatetimeString
from libs.login import login_required
from models.model import Advertising
from services.advertising_service import AdvertisingService

ALLOW_APP_STATUS = ["normal", "abnormal"]

headers = {
    'Authorization': f'Bearer {os.getenv("CONSUMER_API_TOKEN")}',
    'Content-Type': 'application/json; charset=UTF-8'  # 指定编码为 UTF-8
}

def sync_ad_request(ad_data):
    url_prefix = os.getenv("CONSUMER_API_PREFIX")
    url = f"{url_prefix}/admin/advertising/sync"

    response = requests.post(url, json=ad_data, headers=headers)

    # 检查请求是否成功
    if response.status_code == 200:
        logging.info('成功:', response.json())  # 打印响应的 JSON 数据
    else:
        logging.error('请求失败，状态码:', response.status_code)

def sync_ad_status(ad_id, status):
    url_prefix = os.getenv("CONSUMER_API_PREFIX")
    url = f"{url_prefix}/admin/advertising/sync/{ad_id}/status"

    request_data = {"status": status}
    response = requests.put(url, json=request_data, headers=headers)
    # 检查请求是否成功
    if response.status_code == 200:
        logging.info('成功:', response.json())  # 打印响应的 JSON 数据
    else:
        logging.error('请求失败，状态码:', response.status_code)

def sync_ad_delete(ad_id):
    url_prefix = os.getenv("CONSUMER_API_PREFIX")
    url = f"{url_prefix}/admin/advertising/sync/{ad_id}/delete"

    response = requests.delete(url, headers=headers)
    # 检查请求是否成功
    if response.status_code == 200:
        logging.info('成功:', response.json())  # 打印响应的 JSON 数据
    else:
        logging.error('请求失败，状态码:', response.status_code)


class AdvertisingListApi(Resource):
    @setup_required
    @login_required
    @account_initialization_required
    def get(self):
        parser = reqparse.RequestParser()
        parser.add_argument("page", type=inputs.int_range(1, 99999), required=False, default=1, location="args")
        parser.add_argument("limit", type=inputs.int_range(1, 100), required=False, default=20, location="args")
        args = parser.parse_args()

        advertising_service = AdvertisingService()
        advertising_pagination = advertising_service.get_paginate_advertising(args)

        if not advertising_pagination:
            return {"data": [], "total": 0, "page": 1, "limit": 20, "has_more": False}

        return marshal(advertising_pagination, advertising_pagination_fields)

    @setup_required
    @login_required
    @account_initialization_required
    def post(self):
        # 添加ad
        parser = reqparse.RequestParser()

        parser.add_argument('weigh', type=int, choices=range(1, 99999), location='json')
        parser.add_argument('icon', type=str, location='json')
        parser.add_argument('started_time', type=DatetimeString("%Y-%m-%d %H:%M:%S"), location='json')
        parser.add_argument('ended_time', type=DatetimeString("%Y-%m-%d %H:%M:%S"), location='json')
        parser.add_argument('redirect_url', type=str,  location='json')

        # 你可以在 API 处理函数中调用 `parser.parse_args()` 来获取参数
        args = parser.parse_args()
        if not current_user.is_editor:
            raise Forbidden()

        # 然后可以访问这些参数
        advertising_service = AdvertisingService()
        ad = advertising_service.create_ad(args, current_user)
        ad_data = {
            'id': ad.id,
            'weigh': args['weigh'],
            'icon': args['icon'],
            'started_time': args['started_time'],
            'ended_time': args['ended_time'],
            'redirect_url': args['redirect_url'],
            'status': 'normal'
        }
        sync_ad_request(ad_data)
        return marshal(ad, advertising_partial_fields)

class AdvertisingApi(Resource):
    @setup_required
    @login_required
    @account_initialization_required
    def get(self, ad_id):
        ad_model = db.session.query(Advertising).filter(Advertising.id == ad_id).first()
        if ad_model is None:
            return AdNotFoundError

        return marshal(ad_model, advertising_detail_fields)

    @setup_required
    @login_required
    @account_initialization_required
    def put(self, ad_id):

        ad_model = db.session.query(Advertising).filter(Advertising.id == ad_id).first()
        if ad_model is None:
            return AdNotFoundError

        if not current_user.is_editor:
            raise Forbidden()

        parser = reqparse.RequestParser()
        parser.add_argument('weigh', type=int, choices=range(1, 99999),location='json')
        parser.add_argument('icon', type=str,  location='json')
        parser.add_argument('icon_type', type=str, location='json')
        parser.add_argument('started_time', type=DatetimeString("%Y-%m-%d %H:%M:%S"), location='json')
        parser.add_argument('ended_time', type=DatetimeString("%Y-%m-%d %H:%M:%S"), location='json')
        parser.add_argument('status', type=str, choices=ALLOW_APP_STATUS, location='json')
        parser.add_argument('redirect_url', type=str, help='URL to redirect to', location='json')
        args = parser.parse_args()

        advertising_service = AdvertisingService()
        advertising_service.update_ad(args, ad_model, current_user)

        ad_data = {
            'id': ad_model.id,
            'weigh': args['weigh'],
            'icon': args['icon'],
            'started_time': args['started_time'],
            'ended_time': args['ended_time'],
            'redirect_url': args['redirect_url'],
            'status': 'normal'
        }
        sync_ad_request(ad_data)
        return marshal(ad_model, advertising_detail_fields)

    @setup_required
    @login_required
    @account_initialization_required
    def delete(self, ad_id):
        ad_model = db.session.query(Advertising).filter(Advertising.id == ad_id).first()
        if ad_model is None:
            return AdNotFoundError

        db.session.delete(ad_model)
        db.session.commit()

        sync_ad_delete(ad_id)
        return {"result": "success"}, 204

class AdvertisingStatus(Resource):
    @setup_required
    @login_required
    @account_initialization_required
    def put(self, ad_id):
        parser = reqparse.RequestParser()
        parser.add_argument('status', type=str, choices=ALLOW_APP_STATUS, location='json')
        args = parser.parse_args()

        ad_model = db.session.query(Advertising).filter(Advertising.id == ad_id).first()
        if ad_model is None:
            return AdNotFoundError
        ad_model.status = args.get('status')
        db.session.commit()

        sync_ad_status(ad_id, ad_model.status)
        return marshal(ad_model, advertising_detail_fields)

api.add_resource(AdvertisingListApi, "/advertising")
api.add_resource(AdvertisingApi, "/advertising/<uuid:ad_id>")
api.add_resource(AdvertisingStatus, "/advertising/<uuid:ad_id>/status")
