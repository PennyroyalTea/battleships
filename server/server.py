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
    def __init__(self, name):
        self.name = name
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
    if 'room' in local_state[websocket] and local_state[websocket]['room'] is not None:
        rid = local_state[websocket]['room']
        global_state['rooms'][rid].unsubscribe(websocket)
    local_state.pop(websocket)


async def multicast(message, connections):
    if connections:
        await asyncio.wait([asyncio.create_task(connection.send(message)) for connection in connections])
    print(f'multicast > {message}')


async def consumer(message, ws):
    global global_state
    global local_state

    if message['type'] == 'request':                            # requests
        if message['subject'] == 'rooms':
            await ws.send(events.rooms_list(global_state))
        elif message['subject'] == 'room_info':
            if local_state[ws]['room'] is not None:
                await ws.send(events.room_info(global_state['rooms'][local_state[ws]['room']]))
            else:
                await ws.send(events.response_error(f'user not in room'))
        else:
            logging.error(f'unsupported subject: {subject}')
    elif message['type'] == 'update':                           # updates
        if message['subject'] == 'rooms':
            global_state['rooms'].append(Room(f'{len(global_state["rooms"])}'))
            await ws.send(events.response_ok())
        elif message['subject'] == 'connect_to_room':
            id = message['content']
            if not id.isnumeric() or int(id) >= len(global_state['rooms']):
                await ws.send(events.response_error(f'{id} is not a room'))
            elif global_state['rooms'][int(id)].state == 'closed':
                await ws.send(events.response_error(f'room {id} is closed'))
            else:
                global_state['rooms'][int(id)].subscribe(ws)
                local_state[ws]['room'] = int(id)
                await ws.send(events.response_ok())
                await multicast(events.room_info(global_state['rooms'][local_state[ws]['room']]),
                                global_state['rooms'][local_state[ws]['room']].connections)
        elif message['subject'] == 'ready':
            if message['content'] == '+':
                global_state['rooms'][local_state[ws]['room']].readycnt += 1
            else:
                global_state['rooms'][local_state[ws]['room']].readycnt -= 1
            await multicast(
                events.room_info(global_state['rooms'][local_state[ws]['room']]),
                global_state['rooms'][local_state[ws]['room']].connections)
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