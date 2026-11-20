def test_workbench_exposes_actions_and_both_samples(client):
    response = client.get('/')
    assert response.status_code == 200
    assert all(text in response.text for text in ['期刊到藏校对册', '证据寄送', '归档本次勾稽', '十一月补刊清单', '验收清册'])
    assert client.get('/static/desk.js').status_code == 200


def test_workbench_exposes_cross_year_note_panel_and_sample(client):
    response = client.get('/')
    assert all(text in response.text for text in [
        '跨年出版说明', '出版说明', '跨年合期清册', 'note-status-labels', 'notes-panel'])
    assert client.get('/api/notes/crossyear').status_code == 200
    assert client.get('/static/evidence.js').status_code == 200
