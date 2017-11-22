import msgpack


def get_msgpack_hooks(custom_encdec_list):
    """ [(ordinal_num, type, encoder, decoder), ]"""

    def default(obj):
        for num, c_type, encoder, _ in custom_encdec_list:
            if isinstance(obj, c_type):
                return msgpack.ExtType(num, encoder(obj))
        raise TypeError("Unknown type: {}".format(obj))

    def ext_hook(code, data):
        for num, _, _, decoder in custom_encdec_list:
            if num == code:
                return decoder(data)
        return msgpack.ExtType(code, data)

    return default, ext_hook
