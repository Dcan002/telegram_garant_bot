import sqlalchemy
from sqlalchemy import orm

from .db_session import SqlAlchemyBase


class Contracts(SqlAlchemyBase):
    __tablename__ = 'contracts'

    id = sqlalchemy.Column(sqlalchemy.Integer,
                           primary_key=True, autoincrement=True)
    title = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    content = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    cost = sqlalchemy.Column(sqlalchemy.Integer)
    is_closed = sqlalchemy.Column(sqlalchemy.Boolean, default=False)
    file = sqlalchemy.Column(sqlalchemy.String, nullable=True)

    user_id1 = sqlalchemy.Column(sqlalchemy.Integer,
                                  sqlalchemy.ForeignKey("users.id"))
    user_id2 = sqlalchemy.Column(sqlalchemy.Integer)

    #status_id1 = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    #status_id2 = sqlalchemy.Column(sqlalchemy.String, nullable=True)

    status = sqlalchemy.Column(sqlalchemy.String)
    user = orm.relation('User')

    # contracts