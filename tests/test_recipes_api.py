SAMPLE_RECIPE = {
    'name': 'Chicken Stir Fry',
    'base_servings': 2,
    'ingredients': [{'name': 'chicken', 'quantity': 300, 'unit': 'g', 'category': 'protein'}],
    'cook_method': ['stove'],
    'prep_time_mins': 15,
    'cook_time_mins': 20,
    'makes_leftovers': False,
    'tags': ['quick'],
}

def test_list_recipes_empty(client):
    resp = client.get('/api/recipes')
    assert resp.status_code == 200
    assert resp.get_json() == []

def test_create_recipe(client):
    resp = client.post('/api/recipes', json=SAMPLE_RECIPE)
    assert resp.status_code == 201
    data = resp.get_json()
    assert data['name'] == 'Chicken Stir Fry'
    assert data['base_servings'] == 2
    assert 'id' in data

def test_get_recipe(client):
    create_resp = client.post('/api/recipes', json=SAMPLE_RECIPE)
    recipe_id = create_resp.get_json()['id']
    resp = client.get(f'/api/recipes/{recipe_id}')
    assert resp.status_code == 200
    assert resp.get_json()['name'] == 'Chicken Stir Fry'

def test_get_recipe_not_found(client):
    resp = client.get('/api/recipes/999')
    assert resp.status_code == 404

def test_update_recipe(client):
    create_resp = client.post('/api/recipes', json=SAMPLE_RECIPE)
    recipe_id = create_resp.get_json()['id']
    resp = client.put(f'/api/recipes/{recipe_id}', json={'name': 'Beef Stir Fry', 'makes_leftovers': True})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['name'] == 'Beef Stir Fry'
    assert data['makes_leftovers'] is True

def test_delete_recipe(client):
    create_resp = client.post('/api/recipes', json=SAMPLE_RECIPE)
    recipe_id = create_resp.get_json()['id']
    del_resp = client.delete(f'/api/recipes/{recipe_id}')
    assert del_resp.status_code == 204
    assert client.get(f'/api/recipes/{recipe_id}').status_code == 404

def test_create_recipe_missing_name(client):
    resp = client.post('/api/recipes', json={})
    assert resp.status_code == 400
    assert 'error' in resp.get_json()
