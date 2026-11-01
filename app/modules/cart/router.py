from fastapi import APIRouter, Depends, Path
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.modules.cart import service
from app.modules.cart.schemas import CartItemAddIn, CartItemUpdateIn, CartOut

router = APIRouter(prefix="/cart", tags=["购物车"])


@router.get("", response_model=CartOut, summary="查看购物车")
def get_cart(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> CartOut:
    return service.get_cart(db, user)


@router.post("/items", response_model=CartOut, summary="加入购物车（同商品累加）")
def add_item(
    data: CartItemAddIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CartOut:
    return service.add_item(db, user, data.product_id, data.quantity)


@router.patch("/items/{item_id}", response_model=CartOut, summary="修改数量")
def update_item(
    data: CartItemUpdateIn,
    item_id: int = Path(ge=1),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CartOut:
    return service.update_item(db, user, item_id, data.quantity)


@router.delete("/items/{item_id}", response_model=CartOut, summary="删除单项")
def remove_item(
    item_id: int = Path(ge=1),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CartOut:
    return service.remove_item(db, user, item_id)


@router.delete("", response_model=CartOut, summary="清空购物车")
def clear_cart(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> CartOut:
    return service.clear_cart(db, user)
