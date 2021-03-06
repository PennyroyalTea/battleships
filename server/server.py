import asyncio
import websockets
import logging
import json

import events

logging.basicConfig()

CONNECTIONS = set()

global_state = {
    'rooms': []
}

local_state = dict()


class Room:
    def __init__(self, name, size):
        self.name = name
        self.size = size
        self.state = 'open'
        self.connections = []
        self.connection_to_field_private = dict()
        self.connection_to_field_public = dict()
        self.connection_to_dead = dict()

    def close(self):
        self.state = 'closed'

    def start_game(self):
        self.cur = 0

    def subscribe(self, ws):
        self.connections.append(ws)

    def unsubscribe(self, ws):
        self.connections.remove(ws)
        self.connection_to_dead.pop(ws)
        self.connection_to_field_private.pop(ws)
        self.connection_to_field_public.pop(ws)
        if len(self.connections) == 0:
            self.state = 'open'


async def register_connection(websocket):
    CONNECTIONS.add(websocket)
    global local_state
    local_state[websocket] = {
        'room': None
    }


async def unregister_connection(websocket):
    CONNECTIONS.remove(websocket)
    global global_state
    global local_state
    if 'room' in local_state[websocket] and local_state[websocket]['room'] is not None:
        rid = local_state[websocket]['room']
        global_state['rooms'][rid].unsubscribe(websocket)
    local_state.pop(websocket)


async def multicast(message, connections):
    if connections:
        await asyncio.wait([asyncio.create_task(connection.send(message)) for connection in connections])
    print(f'multicast > {message}')


async def multicast_with_id(message_obj, connections):
    messages = [json.dumps({'id': i, 'message': message_obj}) for i, _ in enumerate(connections)]
    if connections:
        await asyncio.wait(
            [asyncio.create_task(connection.send(message)) for message, connection in zip(messages, connections)]
        )
    print(f'multicast w id > {message_obj}')


def s_to_pair(s): # 'C6' -> (2, 6)
    return ord(s[0]) - ord('A'), int(s[1])


def possible_shot(from_field, to_cell):
    to_x, to_y = to_cell
    for y, l in enumerate(from_field):
        for x, val in enumerate(l):
            if val not in ['.', 'x'] and abs(y - to_y) + abs(x - to_x) <= int(val):
                return True
    return False


async def request_rooms(global_state, local_state, message, ws):
    await ws.send(events.rooms_list(global_state))


async def request_room_info(global_state, local_state, message, ws):
    if local_state[ws]['room'] is not None:
        await ws.send(events.room_info(global_state['rooms'][local_state[ws]['room']]))
    else:
        await ws.send(events.response_error(f'user not in room'))


async def update_rooms(global_state, local_state, message, ws):
    global_state['rooms'].append(Room(
        name=f'{len(global_state["rooms"])}',
        size=int(message['content'])
    ))
    await ws.send(events.response_ok())


async def connect_to_room(global_state, local_state, message, ws):
    id = message['content']
    if not id.isnumeric() or int(id) >= len(global_state['rooms']):
        await ws.send(events.response_error(f'{id} is not a room'))
    elif global_state['rooms'][int(id)].state == 'closed':
        await ws.send(events.response_error(f'room {id} is closed'))
    else:
        global_state['rooms'][int(id)].subscribe(ws)
        local_state[ws]['room'] = int(id)
        room = global_state['rooms'][local_state[ws]['room']]
        await ws.send(events.response_ok())

        if len(room.connections) >= room.size:
            room.close()
            await multicast(events.start_game(),
                            room.connections)
        else:
            await multicast(events.room_info(room),
                            room.connections)


async def register_field(global_state, local_state, message, ws):
    field = json.loads(message['content'])

    if 'room' not in local_state[ws] or local_state[ws]['room'] is None:
        logging.error('user not in room')

    room = global_state['rooms'][local_state[ws]['room']]
    room.connection_to_field_private[ws] = field
    room.connection_to_field_public[ws] = [['?'] * 10 for _ in range(10)]
    room.connection_to_dead[ws] = False

    if len(room.connection_to_field_private) == len(room.connections):
        room.start_game()
        await multicast(events.start_game(), room.connections)
        await multicast_with_id(events.game_state(room), room.connections)


async def shot(global_state, local_state, message, ws):
    room = global_state['rooms'][local_state[ws]['room']]
    if ws != room.connections[room.cur]:  # not your turn
        return
    cont = json.loads(message['content'])
    to_id, c = int(cont['to']), cont['c']
    if to_id == room.cur:  # can't shot yourself
        return
    #### process shot
    to_connection = room.connections[to_id]
    shot_pos = s_to_pair(c)
    if possible_shot(room.connection_to_field_private[ws], shot_pos) and \
            room.connection_to_field_private[to_connection][shot_pos[1]][shot_pos[0]] == '#':  # hit!
        room.connection_to_field_public[to_connection][shot_pos[1]][shot_pos[0]] = '#'
        if sum([i.count('#') for i in room.connection_to_field_public[to_connection]]) == 5 + 4 + 3 + 3 + 2:  # finish
            room.connection_to_dead[to_connection] = True
            if list(room.connection_to_dead.values()).count(False) == 1:  # game over
                await multicast_with_id(events.game_finish(room.cur), room.connections)
                return
    elif possible_shot(room.connection_to_field_private[ws], shot_pos):  # miss!
        room.connection_to_field_public[to_connection][shot_pos[1]][shot_pos[0]] = '.'
        while True:
            room.cur = (room.cur + 1) % len(room.connections)
            if not room.connection_to_dead[room.connections[room.cur]]:
                break
    else:  # impossible turn
        pass
    await multicast_with_id(events.game_state(room), room.connections)


async def leave_game(global_state, local_state, message, ws):
    room = global_state['rooms'][local_state[ws]['room']]
    room.unsubscribe(ws)
    local_state[ws]['room'] = None


async def consumer(message, ws):
    global global_state
    global local_state

    if message['type'] == 'request':                            # requests
        if message['subject'] == 'rooms':
            await request_rooms(global_state, local_state, message, ws)
        elif message['subject'] == 'room_info':
            await request_room_info(global_state, local_state, message, ws)
        else:
            logging.error(f'unsupported subject: {message["subbject"]}')
    elif message['type'] == 'update':                           # updates
        if message['subject'] == 'rooms':
            await update_rooms(global_state, local_state, message, ws)
        elif message['subject'] == 'connect_to_room':
            await connect_to_room(global_state, local_state, message, ws)
        elif message['subject'] == 'register_field':
            await register_field(global_state, local_state, message, ws)
        elif message['subject'] == 'shot':
            await shot(global_state, local_state, message, ws)
        elif message['subject'] == 'leave_game':
            await leave_game(global_state, local_state, message, ws)
        else:
            logging.error(f'unsupported subject: {message["subbject"]}')
    else:
        logging.error(f'unsupported subject: {message["subbject"]}')


async def handler(websocket, path):
    await register_connection(websocket)
    try:
        async for message in websocket:
            await consumer(json.loads(message), websocket)
    finally:
        await unregister_connection(websocket)

start_server = websockets.serve(handler, "localhost", 8765, ping_interval=None, ping_timeout=None)

asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()