from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.wishlist import Wishlist


class WishlistService:
    """Service layer for wishlist DB operations."""

    def __init__(self, db: Session):
        self.db = db

    def get_user_wishlist(self, user_id: int) -> List[Wishlist]:
        """Return wishlist items for a user sorted by newest first."""
        return (
            self.db.query(Wishlist)
            .filter(Wishlist.owner_id == user_id)
            .order_by(Wishlist.id.desc())
            .all()
        )

    def find_by_app_id(self, user_id: int, steam_app_id: int) -> Optional[Wishlist]:
        """Find a wishlist item by Steam app id for a user."""
        return (
            self.db.query(Wishlist)
            .filter(
                Wishlist.owner_id == user_id,
                Wishlist.steam_app_id == steam_app_id,
            )
            .first()
        )

    def add_item(self, user_id: int, steam_app_id: int) -> Wishlist:
        """Create and persist a wishlist item."""
        item = Wishlist(steam_app_id=steam_app_id, owner_id=user_id)
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def delete_item(self, user_id: int, item_id: int) -> bool:
        """Delete a wishlist item; return False if it does not exist for user."""
        item = (
            self.db.query(Wishlist)
            .filter(Wishlist.id == item_id, Wishlist.owner_id == user_id)
            .first()
        )

        if not item:
            return False

        self.db.delete(item)
        self.db.commit()
        return True
