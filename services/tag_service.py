import json
import logging
import os
import uuid
from typing import Optional

from flask_login import current_user
from sqlalchemy import func
from werkzeug.exceptions import NotFound

from extensions.ext_database import db
from models.dataset import Dataset
from models.model import App, Tag, TagBinding
import requests


def sync_tag(sync_tag_request):
    api_token = os.getenv("CONSUMER_API_TOKEN")
    url_prefix = os.getenv("CONSUMER_API_PREFIX") + "/admin/tags/sync"
    headers = {
        'Authorization': f'Bearer {api_token}',
    }
    response = requests.post(url_prefix, headers=headers, json=sync_tag_request)
    # 检查请求是否成功
    if response.status_code == 200:
        logging.info('成功:', response.json())  # 打印响应的 JSON 数据
    else:
        logging.error('请求失败，状态码:', response.status_code)

def delete_tag_binding_invoke(remove_tag_binding):
    api_token = os.getenv("CONSUMER_API_TOKEN")
    url_prefix = os.getenv("CONSUMER_API_PREFIX") + "/admin/tags/sync/delete/binding"
    headers = {
        'Authorization': f'Bearer {api_token}',
    }

    response = requests.delete(url_prefix, json=remove_tag_binding, headers=headers)
    # 检查请求是否成功
    if response.status_code == 200:
        logging.info('成功:', response.json())  # 打印响应的 JSON 数据
    else:
        logging.error('请求失败，状态码:', response.status_code)


def sync_delete_tags_request(tag_id):
    api_token = os.getenv("CONSUMER_API_TOKEN")
    url_prefix = f"{os.getenv('CONSUMER_API_PREFIX')}/admin/tags/sync/delete/{tag_id}"
    headers = {
        'Authorization': f'Bearer {api_token}',
    }

    response = requests.delete(url_prefix, headers=headers)
    # 检查请求是否成功
    if response.status_code == 200:
        logging.info('成功:', response.json())  # 打印响应的 JSON 数据
    else:
        logging.error('请求失败，状态码:', response.status_code)


class TagService:
    @staticmethod
    def get_tags(tag_type: str, current_tenant_id: str, keyword: Optional[str] = None) -> list:
        query = (
            db.session.query(Tag.id, Tag.type, Tag.name, func.count(TagBinding.id).label("binding_count"))
            .outerjoin(TagBinding, Tag.id == TagBinding.tag_id)
            .filter(Tag.type == tag_type, Tag.tenant_id == current_tenant_id)
        )
        if keyword:
            query = query.filter(db.and_(Tag.name.ilike(f"%{keyword}%")))
        query = query.group_by(Tag.id)
        results = query.order_by(Tag.created_at.desc()).all()
        return results

    @staticmethod
    def get_target_ids_by_tag_ids(tag_type: str, current_tenant_id: str, tag_ids: list) -> list:
        tags = (
            db.session.query(Tag)
            .filter(Tag.id.in_(tag_ids), Tag.tenant_id == current_tenant_id, Tag.type == tag_type)
            .all()
        )
        if not tags:
            return []
        tag_ids = [tag.id for tag in tags]
        tag_bindings = (
            db.session.query(TagBinding.target_id)
            .filter(TagBinding.tag_id.in_(tag_ids), TagBinding.tenant_id == current_tenant_id)
            .all()
        )
        if not tag_bindings:
            return []
        results = [tag_binding.target_id for tag_binding in tag_bindings]
        return results

    @staticmethod
    def get_tags_by_target_id(tag_type: str, current_tenant_id: str, target_id: str) -> list:
        tags = (
            db.session.query(Tag)
            .join(TagBinding, Tag.id == TagBinding.tag_id)
            .filter(
                TagBinding.target_id == target_id,
                TagBinding.tenant_id == current_tenant_id,
                Tag.tenant_id == current_tenant_id,
                Tag.type == tag_type,
            )
            .all()
        )

        return tags or []

    @staticmethod
    def save_tags(args: dict) -> Tag:
        tag = Tag(
            id=str(uuid.uuid4()),
            name=args["name"],
            type=args["type"],
            created_by=current_user.id,
            tenant_id=current_user.current_tenant_id,
        )
        db.session.add(tag)
        db.session.commit()
        return tag

    @staticmethod
    def update_tags(args: dict, tag_id: str) -> Tag:
        tag = db.session.query(Tag).filter(Tag.id == tag_id).first()
        if not tag:
            raise NotFound("Tag not found")
        tag.name = args["name"]
        db.session.commit()
        return tag

    @staticmethod
    def get_tag_binding_count(tag_id: str) -> int:
        count = db.session.query(TagBinding).filter(TagBinding.tag_id == tag_id).count()
        return count

    @staticmethod
    def delete_tag(tag_id: str):
        tag = db.session.query(Tag).filter(Tag.id == tag_id).first()
        if not tag:
            raise NotFound("Tag not found")
        db.session.delete(tag)
        # delete tag binding
        tag_bindings = db.session.query(TagBinding).filter(TagBinding.tag_id == tag_id).all()
        if tag_bindings:
            for tag_binding in tag_bindings:
                db.session.delete(tag_binding)
        db.session.commit()

        sync_delete_tags_request(tag_id)

    @staticmethod
    def save_tag_binding(args):
        # check if target exists
        TagService.check_target_exists(args["type"], args["target_id"])

        sync_tag_request_list = []
        # save tag binding
        for tag_id in args["tag_ids"]:
            tag_binding = (
                db.session.query(TagBinding)
                .filter(TagBinding.tag_id == tag_id, TagBinding.target_id == args["target_id"])
                .first()
            )
            if tag_binding:
                continue
            new_tag_binding = TagBinding(
                tag_id=tag_id,
                target_id=args["target_id"],
                tenant_id=current_user.current_tenant_id,
                created_by=current_user.id,
            )
            TagService.get_tags_by_target_id(args["type"], args["target_id"], new_tag_binding.id)
            db.session.add(new_tag_binding)

            tag = db.session.query(Tag).filter(Tag.id == tag_id).first()
            sync_tag_request = {
                "tag": {
                    "id": tag.id,
                    "name": tag.name,
                    "type": tag.type,
                    "tenant_id": tag.tenant_id,
                },
                "tag_binding": {
                    "id": new_tag_binding.id,
                    "target_id": new_tag_binding.target_id,
                    "tenant_id": new_tag_binding.tenant_id,
                    "tag_id": new_tag_binding.tag_id,
                },
            }
            sync_tag_request_list.append(sync_tag_request)

        # 同步标签到用户端
        sync_tag(sync_tag_request_list)
        db.session.commit()

    @staticmethod
    def delete_tag_binding(args):
        # check if target exists
        TagService.check_target_exists(args["type"], args["target_id"])
        # delete tag binding
        tag_bindings = (
            db.session.query(TagBinding)
            .filter(TagBinding.target_id == args["target_id"], TagBinding.tag_id == (args["tag_id"]))
            .first()
        )
        if tag_bindings:
            db.session.delete(tag_bindings)
            db.session.commit()

            remove_tag_binding = {
                'tag_id': args["tag_id"],
                "type": args["type"],
                "target_id": args["target_id"],
            }
            delete_tag_binding_invoke(remove_tag_binding)

    @staticmethod
    def check_target_exists(type: str, target_id: str):
        if type == "knowledge":
            dataset = (
                db.session.query(Dataset)
                .filter(Dataset.tenant_id == current_user.current_tenant_id, Dataset.id == target_id)
                .first()
            )
            if not dataset:
                raise NotFound("Dataset not found")
        elif type == "app":
            app = (
                db.session.query(App)
                .filter(App.tenant_id == current_user.current_tenant_id, App.id == target_id)
                .first()
            )
            if not app:
                raise NotFound("App not found")
        else:
            raise NotFound("Invalid binding type")
