from marshmallow import Schema, fields


class PlayerSchema(Schema):
    id = fields.Int(required=True)
    tg_id = fields.Int(required=True)
    username = fields.Str(required=True)
    balance = fields.Int(required=True)


class PlayersListSchema(Schema):
    players = fields.Nested(PlayerSchema, many=True)


class PlayerRequestSchema(Schema):
    username = fields.Str(required=True)
    amount = fields.Int(required=True)


class ChatSchema(Schema):
    chat_id = fields.Int(required=False)
    num_players = fields.Int(required=False)
