from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app import crud, schemas
from app.database import get_db
from app import taobao_client

router = APIRouter(prefix="/integrations/taobao", tags=["integrations-taobao"])


@router.get("/config", response_model=schemas.TaobaoIntegrationConfigRead)
def get_taobao_config(db: Session = Depends(get_db)):
    return crud.read_taobao_integration_config(db)


@router.put("/config", response_model=schemas.TaobaoIntegrationConfigRead)
def put_taobao_config(payload: schemas.TaobaoIntegrationConfigUpdate, db: Session = Depends(get_db)):
    crud.update_taobao_integration_config(db, payload)
    return crud.read_taobao_integration_config(db)


@router.post("/oauth-url", response_model=schemas.TaobaoOAuthUrlResponse)
def post_taobao_oauth_url(db: Session = Depends(get_db)):
    cfg = crud.get_or_create_integration_settings(db)
    if not cfg.taobao_app_key or not cfg.taobao_app_secret or not (cfg.taobao_redirect_uri or "").strip():
        raise HTTPException(status_code=400, detail="请先填写 App Key、App Secret 与回调地址（与开放平台应用配置完全一致）")
    state = crud.create_taobao_oauth_state(db)
    url = taobao_client.build_authorize_url(cfg.taobao_app_key.strip(), cfg.taobao_redirect_uri.strip(), state)
    return schemas.TaobaoOAuthUrlResponse(authorization_url=url)


@router.get("/callback")
def taobao_oauth_callback(code: str = "", state: str = "", db: Session = Depends(get_db)):
    """淘宝授权回调：请在开放平台将回调 URL 配置为本接口完整地址。"""
    if not code or not state:
        return RedirectResponse(url="/ui/settings/integrations?sales_platform=taobao_error&reason=missing_code", status_code=302)
    if not crud.consume_oauth_state(db, "taobao", state):
        return RedirectResponse(url="/ui/settings/integrations?sales_platform=taobao_error&reason=bad_state", status_code=302)
    cfg = crud.get_or_create_integration_settings(db)
    if not cfg.taobao_app_key or not cfg.taobao_app_secret or not (cfg.taobao_redirect_uri or "").strip():
        return RedirectResponse(url="/ui/settings/integrations?sales_platform=taobao_error&reason=no_config", status_code=302)
    try:
        token = taobao_client.oauth_exchange_code(
            cfg.taobao_app_key.strip(),
            cfg.taobao_app_secret.strip(),
            code,
            cfg.taobao_redirect_uri.strip(),
        )
    except RuntimeError as e:
        return RedirectResponse(
            url="/ui/settings/integrations?sales_platform=taobao_error&reason=" + quote(str(e)[:200], safe=""),
            status_code=302,
        )
    crud.save_taobao_oauth_token(db, token)
    return RedirectResponse(url="/ui/settings/integrations?sales_platform=taobao_ok", status_code=302)
