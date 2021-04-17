from .Exceptions import BFSemanticError
from .General import get_variable_from_ID_token, dimensions_to_size

structs = dict()  # Global dictionary of struct_name --> Struct object


class Struct:
    def __init__(self, name, name_token):
        self.name = name
        self.fields = []
        self.name_token = name_token
        self.size = 0

    def add_field(self, field_type, field_name):
        dimensions = dimensions_to_size(field_type["dimensions"])
        self.size += field_type["size"] * dimensions
        self.fields += [(
            field_type,
            field_name
        )]

    def get_field(self, name):
        for field_type, field_name in self.fields:
            if field_name == name:
                return field_type

        return None

    def is_field_array(self, name):
        dimensions = self.get_field_dimensions(name)

        return dimensions != [1]

    def get_field_dimensions(self, name):
        field = self.get_field(name)

        if field is None:
            return None

        return field["dimensions"]

    def get_field_size(self, name):
        field = self.get_field(name)

        if field is None:
            return None

        return field["size"]


def insert_struct_object(struct):
    if check_if_struct_name_exists(struct.name):
        raise BFSemanticError("Struct '%s' already exists" % struct.name_token)

    structs[struct.name] = struct


def get_struct_object(name):
    return structs[name]


def check_if_struct_name_exists(struct_name):
    return struct_name in structs


def get_offsets(struct_object):
    offsets = {}
    acu = 0
    for field_type, field_name in struct_object.fields:
        size = field_type["size"]
        offsets[field_name] = acu
        acu += size

    return offsets


def get_offset_to_field(struct_object, field_name):
    offsets = get_offsets(struct_object)

    if field_name not in offsets:
        raise BFSemanticError("Field '%s' of struct '%s' doesn't exist" % (field_name, struct_object.name_token))

    return offsets[field_name]


def get_struct_from_id_token(ids_map_list, id_token):
    variable = get_variable_from_ID_token(ids_map_list, id_token)
    return variable.extra
