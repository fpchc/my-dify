from flask_restful import fields

from libs.helper import AppIconUrlField, TimestampField

advertising_partial_fields = {
    "id": fields.String,
    "weigh": fields.Integer,
    "icon": AppIconUrlField,
    "started_time": TimestampField,
    "ended_time": TimestampField,
    "status": fields.String,
    "redirect_url": fields.String,
    "created_by": fields.String,
    "updated_by": fields.String,
    "created_at": TimestampField,
    "updated_at": TimestampField,
}

advertising_pagination_fields = {
    "page": fields.Integer,
    "limit": fields.Integer(attribute="per_page"),
    "total": fields.Integer,
    "has_more": fields.Boolean(attribute="has_next"),
    "data": fields.List(fields.Nested(advertising_partial_fields), attribute="items"),
}

advertising_detail_fields = {
    "id": fields.String,
    "weigh": fields.Integer,
    "icon": AppIconUrlField,
    "icon_type": fields.String,
    "started_time": TimestampField,
    "ended_time": TimestampField,
    "status": fields.String,
    "redirect_url": fields.String,
    "created_by": fields.String,
    "updated_by": fields.String,
    "created_at": TimestampField,
    "updated_at": TimestampField,
}



