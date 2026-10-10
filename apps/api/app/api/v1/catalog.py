from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.deps import Principal, any_member
from app.db.session import get_db
from app.models import Product
from app.schemas.api import ProductOut

router = APIRouter(prefix="/products", tags=["catalog"])


@router.get("", response_model=list[ProductOut])
def list_products(
    principal: Principal = Depends(any_member), db: Session = Depends(get_db)
) -> list[ProductOut]:
    rows = db.scalars(
        select(Product)
        .where(Product.merchant_id == principal.merchant_id, Product.active.is_(True))
        .order_by(Product.price_minor)
    )
    return [ProductOut.model_validate(p) for p in rows]
