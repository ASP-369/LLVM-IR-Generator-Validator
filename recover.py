import json

with open("/home/muzzy/.gemini/antigravity-ide/brain/9a4ebafb-4ab8-4d30-989f-328e4fe1afca/.system_generated/logs/transcript.jsonl") as f:
    for line in f:
        try:
            data = json.loads(line)
            if "tool_calls" in data:
                for call in data["tool_calls"]:
                    if call["name"] == "replace_file_content" or call["name"] == "multi_replace_file_content":
                        args = call["args"]
                        if "ReplacementContent" in args and ("_fix_gep_index_types" in args["ReplacementContent"] or "_dedupe_declare" in args["ReplacementContent"]):
                            print(args["ReplacementContent"])
        except Exception:
            pass
