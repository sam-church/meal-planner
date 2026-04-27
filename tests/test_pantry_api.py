import json

def test_list_pantry_empty(client):
    resp = client.get('/api/pantry')
    assert resp.status_code == 200
    assert resp.get_json() == []

def test_add_pantry_staple(client):
    resp = client.post('/api/pantry', json={'ingredient_name': 'olive oil', 'category': 'pantry'})
    assert resp.status_code == 201
    data = resp.get_json()
    assert data['ingredient_name'] == 'olive oil'
    assert data['category'] == 'pantry'
    assert 'id' in data

def test_list_pantry_after_add(client):
    client.post('/api/pantry', json={'ingredient_name': 'salt', 'category': 'pantry'})
    resp = client.get('/api/pantry')
    assert resp.status_code == 200
    items = resp.get_json()
    assert len(items) == 1
    assert items[0]['ingredient_name'] == 'salt'

def test_delete_pantry_staple(client):
    add_resp = client.post('/api/pantry', json={'ingredient_name': 'pepper'})
    staple_id = add_resp.get_json()['id']
    del_resp = client.delete(f'/api/pantry/{staple_id}')
    assert del_resp.status_code == 204
    list_resp = client.get('/api/pantry')
    assert list_resp.get_json() == []

def test_delete_nonexistent_pantry_staple(client):
    resp = client.delete('/api/pantry/999')
    assert resp.status_code == 404
