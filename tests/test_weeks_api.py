def test_list_weeks_empty(client):
    resp = client.get('/api/weeks')
    assert resp.status_code == 200
    assert resp.get_json() == []

def test_create_week(client):
    resp = client.post('/api/weeks', json={'week_start_date': '2026-04-28'})
    assert resp.status_code == 201
    data = resp.get_json()
    assert data['week_start_date'] == '2026-04-28'
    assert data['slots'] == {}

def test_create_week_duplicate(client):
    client.post('/api/weeks', json={'week_start_date': '2026-04-28'})
    resp = client.post('/api/weeks', json={'week_start_date': '2026-04-28'})
    assert resp.status_code == 409

def test_get_week(client):
    create_resp = client.post('/api/weeks', json={'week_start_date': '2026-04-28'})
    week_id = create_resp.get_json()['id']
    resp = client.get(f'/api/weeks/{week_id}')
    assert resp.status_code == 200
    assert resp.get_json()['week_start_date'] == '2026-04-28'

def test_update_week_slots(client):
    create_resp = client.post('/api/weeks', json={'week_start_date': '2026-04-28'})
    week_id = create_resp.get_json()['id']
    resp = client.put(f'/api/weeks/{week_id}', json={'slots': {'mon_dinner': 1}})
    assert resp.status_code == 200
    assert resp.get_json()['slots']['mon_dinner'] == 1

def test_get_week_not_found(client):
    resp = client.get('/api/weeks/999')
    assert resp.status_code == 404

def test_create_week_missing_date(client):
    resp = client.post('/api/weeks', json={})
    assert resp.status_code == 400
    assert 'error' in resp.get_json()

def test_update_week_not_found(client):
    resp = client.put('/api/weeks/999', json={'slots': {}})
    assert resp.status_code == 404
