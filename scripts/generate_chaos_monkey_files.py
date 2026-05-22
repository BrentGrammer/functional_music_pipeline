import json
import os
import sys

# Ensure functional_music_pipeline is in path if this script is in scripts/
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from transforms.registry import PHRASE_TRANSFORMS, SCORE_TRANSFORMS
from transforms.base import (
    FloatParam, IntegerParam, StringParam, BooleanParam,
    ToneDimensionParam, EnumParam
)

OUTPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'compositions', 'chaos_monkey'))
os.makedirs(OUTPUT_DIR, exist_ok=True)

def generate_bad_value(schema_type):
    """Returns a value that is explicitly INVALID for the given schema."""
    if isinstance(schema_type, FloatParam):
        return True # bool is rejected by FloatParam
    elif isinstance(schema_type, IntegerParam):
        return "not_an_integer"
    elif isinstance(schema_type, StringParam):
        return 123
    elif isinstance(schema_type, BooleanParam):
        return 1.5
    elif isinstance(schema_type, ToneDimensionParam):
        return "NotADimensionEnum"
    elif isinstance(schema_type, EnumParam):
        return "InvalidEnumValueXYZ"
    else:
        return {"an": "object"}

def create_base_config():
    return {
        "motifs": {
            "m1": ["A4"]
        },
        "composition": {
            "voices": [
                {
                    "phrases": [
                        {
                            "motifs": ["m1"]
                        }
                    ]
                }
            ]
        }
    }

def write_json(filename, data):
    path = os.path.join(OUTPUT_DIR, filename)
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)

def generate_parser_bad_files():
    # 1. Not a dict
    write_json("bad_parser_root_type.json", ["not", "a", "dict"])
    
    # 2. Missing motifs
    c2 = create_base_config()
    del c2["motifs"]
    write_json("bad_parser_missing_motifs.json", c2)
    
    # 3. Bad motif format
    c3 = create_base_config()
    c3["motifs"] = [] # should be dict
    write_json("bad_parser_motifs_not_dict.json", c3)

    # 4. Bad voice format
    c4 = create_base_config()
    c4["composition"]["voices"] = {} # should be list
    write_json("bad_parser_voices_not_list.json", c4)

    # 5. Bad phrase motif reference
    c5 = create_base_config()
    c5["composition"]["voices"][0]["phrases"][0]["motifs"] = ["non_existent_motif"]
    write_json("bad_parser_missing_motif_ref.json", c5)

def generate_transform_bad_files():
    for name, descriptor in PHRASE_TRANSFORMS.items():
        if not descriptor.params_spec:
            continue
        for field_name, field_spec in getattr(descriptor.params_spec, "fields", {}).items():
            schema = field_spec.schema
            if isinstance(schema, tuple):
                schema = schema[0] # just use the first schema variant to generate a bad type for both
            
            bad_val = generate_bad_value(schema)
            config = create_base_config()
            config["composition"]["voices"][0]["phrases"][0]["transforms"] = [
                {
                    "name": name,
                    "params": {
                        field_name: bad_val
                    }
                }
            ]
            write_json(f"bad_transform_phrase_{name}_{field_name}.json", config)

    for name, descriptor in SCORE_TRANSFORMS.items():
        if not descriptor.params_spec:
            continue
        for field_name, field_spec in getattr(descriptor.params_spec, "fields", {}).items():
            schema = field_spec.schema
            if isinstance(schema, tuple):
                schema = schema[0]
            
            bad_val = generate_bad_value(schema)
            config = create_base_config()
            config["composition"]["score_transforms"] = [
                {
                    "name": name,
                    "params": {
                        field_name: bad_val
                    }
                }
            ]
            write_json(f"bad_transform_score_{name}_{field_name}.json", config)

if __name__ == "__main__":
    generate_parser_bad_files()
    generate_transform_bad_files()
    print(f"Generated bad config files in {OUTPUT_DIR}")
