def test_list_preferences_empty(client):
    resp = client.get('/api/preferences')
    assert resp.status_code == 200
    assert resp.get_json() == []

def test_add_preference(client):
    resp = client.post('/api/preferences', json={'type': 'like', 'value': 'spicy', 'scope': 'ingredient'})
    assert resp.status_code == 201
    data = resp.get_json()
    assert data['type'] == 'like'
    assert data['value'] == 'spicy'
    assert data['scope'] == 'ingredient'

def test_add_dislike(client):
    resp = client.post('/api/preferences', json={'type': 'dislike', 'value': 'fish', 'scope': 'ingredient'})
    assert resp.status_code == 201
    assert resp.get_json()['type'] == 'dislike'

def test_delete_preference(client):
    add_resp = client.post('/api/preferences', json={'type': 'like', 'value': 'Mediterranean', 'scope': 'cuisine'})
    pref_id = add_resp.get_json()['id']
    del_resp = client.delete(f'/api/preferences/{pref_id}')
    assert del_resp.status_code == 204
    list_resp = client.get('/api/preferences')
    assert list_resp.get_json() == []
