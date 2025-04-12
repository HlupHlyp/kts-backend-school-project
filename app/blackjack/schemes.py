from marshmallow import Schema, fields


class GameSessionModel(Schema):
    __tablename__ = "game_sessions"
    id = fields.Int(required=False)
    chat_id = fields.Int(required=True)
