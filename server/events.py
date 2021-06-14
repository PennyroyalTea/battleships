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
                lambda room: {'state': room.state, 'players': len(room.connections), 'size': room.size},
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
            'size': room.size
        }
    })

def start_game():
    return json.dumps({
        'type': 'response',
        'code': 'ok',
        'content': 'start_game'
    })

def game_state(room):
    return json.dumps({
        'turn': room.cur,
        'fields': list(map(lambda connection: room.connection_to_field_public[connection], room.connections))
    })