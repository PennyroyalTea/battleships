import json


def response_ok(message = None):
    return json.dumps({'type': 'response', 'code': 'ok', 'content': message})


def response_error(message = None):
    return json.dumps({'type': 'response', 'code': 'error', 'content': message})


def rooms_list(global_state):
    return json.dumps({
        'type': 'response',
        'code': 'ok',
        'content': list(
            map(
                lambda room: {'state': room.state, 'players': len(room.connections)},
                global_state['rooms']
            )
        )
    })

def room_info(room):
    return json.dumps({
        'type': 'response',
        'code': 'ok',
        'content': {
            'name': room.name,
            'players': len(room.connections),
            'ready': room.readycnt
        }
    })