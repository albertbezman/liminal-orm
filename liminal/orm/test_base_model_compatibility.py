from datetime import datetime

from sqlalchemy import Column as SqlColumn
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from liminal.enums import BenchlingEntityType
from liminal.enums import BenchlingFieldType as Type
from liminal.enums.benchling_naming_strategy import BenchlingNamingStrategy
from liminal.orm.base import Base
from liminal.orm.base_model import BaseModel
from liminal.orm.base_tables.user import User
from liminal.orm.column import Column
from liminal.orm.mixins import CustomEntityMixin
from liminal.orm.schema_properties import SchemaProperties


def test_base_model_queries_support_declared_dependency_versions() -> None:
    class CompatibilityEntity(BaseModel, CustomEntityMixin):
        __schema_properties__ = SchemaProperties(
            name="Compatibility Entity",
            warehouse_name="compatibility_entity",
            prefix="CompatibilityEntity",
            entity_type=BenchlingEntityType.CUSTOM_ENTITY,
            naming_strategies=[BenchlingNamingStrategy.NEW_IDS],
        )
        notes: SqlColumn = Column(name="Notes", type=Type.TEXT, required=False)

    engine = create_engine("sqlite://")
    Base.metadata.create_all(
        engine, tables=[User.__table__, CompatibilityEntity.__table__]
    )

    with Session(engine) as session:
        session.add(
            User(
                id="user_id",
                created_at=datetime(2024, 1, 1),
                email="user@example.com",
                handle="user",
                is_suspended=False,
                name="Example User",
            )
        )
        session.add_all(
            [
                CompatibilityEntity(
                    id="active_id",
                    archived=False,
                    is_registered=True,
                    creator_id="user_id",
                    notes="example notes",
                ),
                CompatibilityEntity(
                    id="archived_id",
                    archived=True,
                    is_registered=True,
                    creator_id="user_id",
                ),
            ]
        )
        session.commit()

        all_entity_ids = {entity.id for entity in CompatibilityEntity.all(session)}
        active_entities = CompatibilityEntity.apply_base_filters(
            CompatibilityEntity.query(session)
        ).all()
        active_entity_creators = [
            (entity.id, entity.creator.name) for entity in active_entities
        ]
        dataframe = CompatibilityEntity.df(session)

    notes_by_id = dataframe.set_index("id")["notes"]
    assert all_entity_ids == {"active_id", "archived_id"}
    assert active_entity_creators == [("active_id", "Example User")]
    assert notes_by_id["active_id"] == "example notes"
    assert notes_by_id.isna().to_dict() == {"active_id": False, "archived_id": True}
