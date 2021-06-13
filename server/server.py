import asyncio
import websockets
import logging
import json

logging.basicConfig()

CONNECTIONS = set()

global_state = {
    'rooms': []
}

local_state = dict()


class Room:
    def __init__(self):
        self.state = 'open'
        self.connections = []
        self.readycnt = 0

    def close(self):
        self.state = 'closed'

    def subscribe(self, ws):
        self.connections.append(ws)

    def unsubscribe(self, ws):
        self.connections.remove(ws)

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
    if 'room' in local_state[websocket]:
        rid = local_state[websocket]['room']
        global_state['rooms'][rid].unsubscribe(websocket)
    local_state.pop(websocket)


async def multicast(message):
    if CONNECTIONS:
        await asyncio.wait([connection.send(message) for connection in CONNECTIONS])
    print(f'multicast > {message}')


async def consumer(message, ws):
    global global_state

    if message['type'] == 'request':
        if message['subject'] == 'rooms':
            await ws.send(json.dumps({
                'type': 'response',
                'code': 'ok',
                'content': list(map(lambda room: {'state': room.state, 'players': len(room.connections)}, global_state['rooms']))
            }))
        else:
            logging.error(f'unsupported subject: {subject}')
    elif message['type'] == 'update':
        if message['subject'] == 'rooms':
            global_state['rooms'].append(Room())
        elif message['subject'] == 'connect_to_room':
            id = message['content']
            if not id.isnumeric() or int(id) >= len(global_state['rooms']):
                await ws.send(json.dumps({'type': 'response', 'code': 'error', 'content': f'{id} is not a room'}))
            elif global_state['rooms'][int(id)].state == 'closed':
                await ws.send(json.dumps({'type': 'response', 'code': 'error', 'content': f'room {id} is closed'}))
            else:
                global_state['rooms'][int(id)].subscribe(ws)
                local_state[ws]['room'] = int(id)
                await ws.send(json.dumps({'type': 'response', 'code': 'ok'}))
        else:
            logging.error(f'unsupported subject: {subject}')
    else:
        logging.error(f'unsupported subject: {subject}')


async def handler(websocket, path):
    await register_connection(websocket)
    try:
        async for message in websocket:
            await consumer(json.loads(message), websocket)
    finally:
        await unregister_connection(websocket)

start_server = websockets.serve(handler, "localhost", 8765)

asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()