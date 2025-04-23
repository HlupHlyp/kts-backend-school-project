from marshmallow import Schema, fields


class AdminRequestSchema(Schema):
    email = fields.Str(required=True)
    password = fields.Str(required=True, load_only=True)


class AdminSchema(AdminRequestSchema):
    id = fields.Int(required=True)
