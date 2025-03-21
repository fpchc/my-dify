from flask import request
from flask_restful import Resource, marshal_with, reqparse
from flask_restful.inputs import int_range
from werkzeug.exceptions import NotFound

import services
from controllers.service_api import api
from controllers.service_api.app.error import NotChatAppError
from controllers.service_api.wraps import FetchUserArg, WhereisUserArg, validate_app_token
from core.app.entities.app_invoke_entities import InvokeFrom
from fields.conversation_fields import (
    conversation_delete_fields,
    conversation_infinite_scroll_pagination_fields,
    simple_conversation_fields,
)
from libs.helper import uuid_value
from models.model import App, AppMode, EndUser
from services.clients.http_client import delete_conversation
from services.conversation_service import ConversationService


class ConversationApi(Resource):
    @validate_app_token(fetch_user_arg=FetchUserArg(fetch_from=WhereisUserArg.QUERY))
    @marshal_with(conversation_infinite_scroll_pagination_fields)
    def get(self, app_model: App, end_user: EndUser):
        app_mode = AppMode.value_of(app_model.mode)
        if app_mode not in {AppMode.CHAT, AppMode.AGENT_CHAT, AppMode.ADVANCED_CHAT}:
            raise NotChatAppError()

        parser = reqparse.RequestParser()
        parser.add_argument("last_id", type=uuid_value, location="args")
        parser.add_argument("limit", type=int_range(1, 100), required=False, default=20, location="args")
        parser.add_argument(
            "sort_by",
            type=str,
            choices=["created_at", "-created_at", "updated_at", "-updated_at"],
            required=False,
            default="-updated_at",
            location="args",
        )
        args = parser.parse_args()

        try:
            return ConversationService.pagination_by_last_id(
                app_model=app_model,
                user=end_user,
                last_id=args["last_id"],
                limit=args["limit"],
                invoke_from=InvokeFrom.SERVICE_API,
                sort_by=args["sort_by"],
            )
        except services.errors.conversation.LastConversationNotExistsError:
            raise NotFound("Last Conversation Not Exists.")


class ConversationDetailApi(Resource):
    @validate_app_token(fetch_user_arg=FetchUserArg(fetch_from=WhereisUserArg.JSON))
    @marshal_with(conversation_delete_fields)
    def delete(self, app_model: App, end_user: EndUser, c_id):
        app_mode = AppMode.value_of(app_model.mode)
        if app_mode not in {AppMode.CHAT, AppMode.AGENT_CHAT, AppMode.ADVANCED_CHAT}:
            raise NotChatAppError()

        conversation_id = str(c_id)

        try:
            ConversationService.delete(app_model, conversation_id, end_user)
            delete_conversation(conversation_id)
        except services.errors.conversation.ConversationNotExistsError:
            raise NotFound("Conversation Not Exists.")
        return {"result": "success"}, 200


class ConversationRenameApi(Resource):
    @validate_app_token(fetch_user_arg=FetchUserArg(fetch_from=WhereisUserArg.JSON))
    @marshal_with(simple_conversation_fields)
    def post(self, app_model: App, end_user: EndUser, c_id):
        app_mode = AppMode.value_of(app_model.mode)
        if app_mode not in {AppMode.CHAT, AppMode.AGENT_CHAT, AppMode.ADVANCED_CHAT}:
            raise NotChatAppError()

        conversation_id = str(c_id)

        parser = reqparse.RequestParser()
        parser.add_argument("name", type=str, required=False, location="json")
        parser.add_argument("auto_generate", type=bool, required=False, default=False, location="json")
        args = parser.parse_args()

        try:
            return ConversationService.rename(app_model, conversation_id, end_user, args["name"], args["auto_generate"])
        except services.errors.conversation.ConversationNotExistsError:
            raise NotFound("Conversation Not Exists.")

class ConversationDeleteBulkApi(Resource):

    @validate_app_token(fetch_user_arg=FetchUserArg(fetch_from=WhereisUserArg.JSON))
    @marshal_with(conversation_delete_fields)
    def delete(self, app_model: App, end_user: EndUser):
        # 获取应用模式
        app_mode = AppMode.value_of(app_model.mode)
        if app_mode not in {AppMode.CHAT, AppMode.AGENT_CHAT, AppMode.ADVANCED_CHAT}:
            raise NotChatAppError()

        # 从请求体中获取 c_ids 和 user 参数
        data = request.get_json()
        c_ids = data.get("c_ids", [])

        if not c_ids:
            return {"result": "failure", "message": "No conversation ids provided."}, 400

        # 记录删除失败的会话 ID
        failed_ids = []

        for conversation_id in c_ids:
            try:
                # 删除单个会话
                ConversationService.delete(app_model, str(conversation_id), end_user)
                delete_conversation(str(conversation_id))
            except services.errors.conversation.ConversationNotExistsError:
                failed_ids.append(str(conversation_id))  # 记录删除失败的 ID

        if failed_ids:
            # 如果有删除失败的 ID，返回失败的 ID 列表
            return {"result": "success"}, 200

        return {"result": "success"}, 200

api.add_resource(ConversationRenameApi, "/conversations/<uuid:c_id>/name", endpoint="conversation_name")
api.add_resource(ConversationApi, "/conversations")
api.add_resource(ConversationDeleteBulkApi, "/conversations/delete_bulk")
api.add_resource(ConversationDetailApi, "/conversations/<uuid:c_id>", endpoint="conversation_detail")
