#Python Helper functions
#(c) 2023 GizMoCuz

import json

class DatetimeEncoder(json.JSONEncoder):
    def default(self, obj):
        try:
            return super().default(obj)
        except TypeError:
            return str(obj)

def save_dict_to_file(dic, filename):
    with open(filename, 'w', encoding='utf-8') as f: json.dump(dic, f, ensure_ascii=False, indent=4, sort_keys=True, cls=DatetimeEncoder)

def load_dict_from_file(filename):
    try:
        dic = json.load( open( filename ) )
    except Exception as error:
        dic = {}
        print('error opening dict file! :', error )
    return dic

def serialize_dict(dic):
    return json.dumps(dic, ensure_ascii=False, indent=4, sort_keys=True, cls=DatetimeEncoder)