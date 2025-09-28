import re, io, sys, os
p = os.path.join('security','security_headers.py')
s = open(p, 'r', encoding='utf-8').read()
changed = False

# Ensure 're' is imported (in case it wasn't already)
if not re.search(r'^\s*import\s+re\b', s, flags=re.M):
    s = 'import re\\n' + s
    changed = True

# Insert an async helper that just returns the already-built response,
# then replace 'lambda r: response' with that helper.
if 'lambda r: response' in s and '_return_response' not in s:
    s = re.sub(r'(response\s*=\s*await\s+call_next\(request\)\s*)',
               r"\\1    async def _return_response(_):\\n        return response\\n",
               s, count=1, flags=re.S)
    s = s.replace('lambda r: response', '_return_response')
    changed = True

if changed:
    open(p, 'w', encoding='utf-8').write(s)
    print('patched')
else:
    print('no-change')
