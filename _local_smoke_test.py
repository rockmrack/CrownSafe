from fastapi.testclient import TestClient
from api.main_babyshield import app
c = TestClient(app, base_url='http://localhost')
H = {'host':'localhost'}
r = c.get('/healthz', headers=H); print('HEALTH', r.status_code, r.text)
r = c.get('/api/v1/chat/flags', headers=H); print('FLAGS', r.status_code, r.text)
print('VENDOR', c.get('/vendor/phpunit/test', headers=H).status_code)
print('INDEX', c.get('/index.php', headers=H).status_code)
