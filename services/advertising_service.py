from datetime import datetime, UTC

from controllers.console.ad import advertising
from extensions.ext_database import db
from models import Account
from models.model import Advertising, IconType


class AdvertisingService:
    def get_paginate_advertising(self, args: dict):

        advertising_list = db.paginate(
            db.select(Advertising).order_by(Advertising.id.desc()),
            page=args["page"],
            per_page=args["limit"],
            error_out=False)

        return advertising_list

    def create_ad(self, args: dict, account: Account) -> Advertising:

        ad = Advertising()

        ad.name = args.get("name")
        ad.weigh = args.get("weigh")
        ad.icon = args.get("icon")
        ad.icon_type = args.get("icon_type", IconType.IMAGE.value)
        ad.started_time = args.get("started_time")
        ad.ended_time = args.get("ended_time")
        ad.redirect_url = args.get("redirect_url")
        ad.status = "normal"
        ad.created_at = datetime.now(UTC).replace(tzinfo=None)
        ad.created_by = account.id

        db.session.add(ad)
        db.session.flush()

        db.session.commit()
        return ad

    def update_ad(self, args: dict, ad_model: advertising, account: Account) -> Advertising:

        ad_model.name = args.get("name")
        ad_model.weigh = args.get("weigh")
        ad_model.icon = args.get("icon")
        ad_model.started_time = args.get("started_time")
        ad_model.ended_time = args.get("ended_time")
        ad_model.redirect_url = args.get("redirect_url")
        ad_model.updated_by = account.id
        ad_model.updated_at = datetime.now(UTC).replace(tzinfo=None)

        db.session.commit()

        return ad_model

