from flask_restful import Resource, marshal_with, reqparse

from controllers.common import fields
from controllers.common import helpers as controller_helpers
from controllers.service_api import api
from controllers.service_api.app.error import AppUnavailableError
from controllers.service_api.wraps import validate_app_token, \
    validate_out_app_token
from core.file import helpers as file_helpers
from models.model import App, AppMode
from services.app_service import AppService
from extensions.ext_database import db


class AppParameterApi(Resource):
    """Resource for app variables."""

    @validate_app_token
    @marshal_with(fields.parameters_fields)
    def get(self, app_model: App):
        """Retrieve app parameters."""
        if app_model.mode in {AppMode.ADVANCED_CHAT.value, AppMode.WORKFLOW.value}:
            workflow = app_model.workflow
            if workflow is None:
                raise AppUnavailableError()

            features_dict = workflow.features_dict
            user_input_form = workflow.user_input_form(to_old_structure=True)
        else:
            app_model_config = app_model.app_model_config
            if app_model_config is None:
                raise AppUnavailableError()

            features_dict = app_model_config.to_dict()

            user_input_form = features_dict.get("user_input_form", [])

        return controller_helpers.get_parameters_from_feature_dict(
            features_dict=features_dict, user_input_form=user_input_form
        )


class AppMetaApi(Resource):
    @validate_app_token
    def get(self, app_model: App):
        """Get app meta"""
        return AppService().get_app_meta(app_model)


class AppInfoApi(Resource):
    @validate_app_token
    def get(self, app_model: App):
        """Get app information"""
        tags = [tag.name for tag in app_model.tags]
        return {"name": app_model.name, "description": app_model.description, "tags": tags}


    
class OutAppListApi(Resource):
    @validate_out_app_token
    def get(self):
        app_ids = ['7390b1f2-45e7-4c44-9649-5ebd5ddb348c', '7a06baf8-852e-4f13-9ce0-ba1d88173b65']
        
        app_models = db.session.query(App).filter(App.id.in_(app_ids)).all()
         # 只返回 name 和 avatar 字段
        result = [{'name': app.name, 'icon': file_helpers.get_signed_file_url(app.icon), "description": app.description} for app in app_models]
        return result


api.add_resource(OutAppListApi, "/out/apps")
api.add_resource(AppParameterApi, "/parameters")
api.add_resource(AppMetaApi, "/meta")
api.add_resource(AppInfoApi, "/info")
