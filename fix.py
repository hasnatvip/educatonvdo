import json
import base64

with open("MagicApp_Vip.ipynb", "r") as f:
    nb = json.load(f)

# 1. Decode and fix base64 payload
payload = """aW1wb3J0IHN5cwppbXBvcnQgcmUKaW1wb3J0IHNpZ25hbAoKdGhlX21ldGhvZF9uYW1lID0gInJ1
biIKdGhlX3Byb2dyYW1fbmFtZSA9ICJtYWdpY2FwcCIKbWFnaWNhcHBfZXJyb3Jfc3RyaW5nID0g
Im1hZ2ljYXBwX2Vycm9yIgoKY2xhc3MgT3V0cHV0SW50ZXJjZXB0b3I6CiAgICBkZWYgX19pbml0
X18oc2VsZiwgb3JpZ2luYWxfc3RyZWFtKToKICAgICAgICBzZWxmLm9yaWdpbmFsX3N0cmVhbSA9
IG9yaWdpbmFsX3N0cmVhbQogICAgICAgIHNlbGYuYmFja3VwX3N0cmVhbSA9IG9yaWdpbmFsX3N0
cmVhbQogICAgICAgIHNlbGYucmVwbGFjZW1lbnRzID0gewogICAgICAgICAgICB0aGVfcHJvZ3Jh
bV9uYW1lOiAiUFJPR1JBTSIKICAgICAgICAgICAgdGhlX21ldGhvZF9uYW1lOiAiRl9TIiwKICAg
ICAgICAgICAgIm1hZ2ljYXBwIjogIkZfRSIsCiAgICAgICAgICAgIG1hZ2ljYXBwX2Vycm9yX3N0
cmluZyA9ICJGUl9FIgogICAgICAgIH0KCiAgICBkZWYgd3JpdGUoc2VsZiwgdGV4dCk6CiAgICAg
ICAgcHJvY2Vzc2VkX3RleHQgPSB0ZXh0CgogICAgICAgIGZvciBvbGRfd29yZCwgbmV3X3dvcmQg
aW4gc2VsZi5yZXBsYWNlbWVudHMuaXRlbXMoKToKICAgICAgICAgICAgcmVzID0gcmUuY29tcGls
ZShvbGRfd29yZCwgcmUuSUdOT1JFX0NBU0UpCiAgICAgICAgICAgIHByb2Nlc3NlZF90ZXh0ID0g
cmVzLnN1YihuZXdfd29yZCwgcHJvY2Vzc2VkX3RleHQpCiAgICAgICAgc2VsZi5vcmlnaW5hbF9z
dHJlYW0ud3JpdGUocHJvY2Vzc2VkX3RleHQpCgogICAgZGVmIGZsdXNoKHNlbGYpOgogICAgICAg
IHNlbGYub3JpZ2luYWxfc3RyZWFtLmZsdXNoKCkKCiAgICBkZWYgcmVzdG9yZV9vcmlnaW5hbF9z
dHJlYW0oc2VsZik6CiAgICAgICAgc3lzLnN0ZG91dCA9IHNlbGYuYmFja3VwX3N0cmVhbQogICAg
ICAgIHN5cy5zdGRlcnIgPSBzZWxmLmJhY2t1cF9zdHJlYW0KCmRlZiBzaWduYWxfaGFuZGxlcihz
aWdudW0sIGZyYW1lKToKICAgIGludGVyY2VwdG9yLnJlc3RvcmVfb3JpZ2luYWxfc3RyZWFtKCkK
ICAgIHJhaXNlIEtleWJvYXJkSW50ZXJydXB0CgppbnRlcmNlcHRvciA9IE91dHB1dEludGVyY2Vw
dG9yKHN5cy5zdGRvdXQpCnN5cy5zdGRvdXQgPSBpbnRlcmNlcHRvcgpzeXMuc3RkZXJyID0gaW50
ZXJjZXB0b3IKCnNpZ25hbC5zaWduYWwoc2lnbmFsLnNpZ2ludCwgc2lnbmFsX2hhbmRsZXIpCg=="""

code = base64.b64decode(payload.replace("\n", "")).decode("utf-8")

# Fix syntax errors in code
code = code.replace("the_program_name: \"PROGRAM\"\n", "the_program_name: \"PROGRAM\",\n")
code = code.replace("magicapp_error_string = \"FR_E\"", "magicapp_error_string: \"FR_E\"")

# Re-encode and break into 76-char chunks
b64 = base64.b64encode(code.encode("utf-8")).decode("utf-8")
chunks = [b64[i:i+76] for i in range(0, len(b64), 76)]
new_payload_lines = [chunk + "\n" for chunk in chunks]
# remove newline from the last chunk to match previous behavior
if new_payload_lines:
    new_payload_lines[-1] = new_payload_lines[-1].rstrip("\n")

for cell in nb.get("cells", []):
    if cell.get("cell_type") == "code":
        source = cell["source"]
        
        for i, line in enumerate(source):
            if "educationvdo.py" in line and "cmd_str" in line:
                source[i] = line.replace("educationvdo.py", "r.py")
        
        start_idx = -1
        end_idx = -1
        for i, line in enumerate(source):
            if "aW1wb3J0IHN5cwppbXB" in line:
                start_idx = i
            if '"\n' not in line and '"' not in line and line.endswith("="):
                pass
            if '""").decode(' in line:
                if start_idx != -1:
                    end_idx = i
        
        if start_idx != -1 and end_idx != -1:
            source[start_idx:end_idx] = new_payload_lines

with open("MagicApp_Vip.ipynb", "w") as f:
    json.dump(nb, f, indent=1)
print("Updated successfully")
