import asyncio
from aioconsole import ainput
import json
import time
import websockets

import battleships

state = {
    'step': 'lobby'
}


async def lobby(websocket):
    global state

    while True:
        await websocket.send(json.dumps({'type': 'request', 'subject': 'rooms'}))
        response = json.loads(await websocket.recv())
        if response['code'] != 'ok':
            raise Exception(f'Не удается загрузить список комнат, ошибка {response["content"]}')

        rooms = response['content']

        print('Доступные комнаты:')
        print('-' * 16)
        for i, room in enumerate(rooms):
            print(f'Комната #{i}: {room["players"]} / {room["size"]} игроков, {"открыта" if room["state"] == "open" else "закрыта"}')
        print('-' * 16)

        while True:
            resp = input('Введите номер комнаты, чтобы присоединиться к ней.\n '
                         'Введите "new [размер]", чтобы создать новую.\n '
                         'Введите "upd", чтобы обновить список комнат.')
            tokens = resp.split(' ')
            if len(tokens) == 2 and tokens[0] == 'new' and tokens[1].isnumeric():
                await websocket.send(json.dumps({'type': 'update', 'subject': 'rooms', 'content': tokens[1]}))
                await websocket.recv()
                break
            elif tokens[0] == 'upd':
                break
            elif tokens[0].isnumeric() and int(tokens[0]) < len(rooms):
                await websocket.send(json.dumps({'type': 'update', 'subject': 'connect_to_room', 'content': tokens[0]}))
                res = json.loads(await websocket.recv())
                if res['code'] == 'error':
                    print(f'Ошибка при входе в комнату: {res["content"]}')
                else:
                    state['step'] = 'room_wait'
                    break
            else:
                print(f'Такой комнаты нет: {resp}, попробуйте снова')
                continue
        if state['step'] != 'lobby':
            break


async def room_wait(websocket):
    global state

    room = json.loads(await websocket.recv())['content']
    while room != 'start_game':
        print(f'Вы в комнате {room["name"]} [{room["players"]} / {room["size"]}].')
        room = json.loads(await websocket.recv())['content']
    state['step'] = 'room_prep'


async def room_prep(websocket):
    global state

    field = battleships.read()
    await websocket.send(json.dumps({'type': 'update', 'subject': 'register_field', 'content': json.dumps(field)}))
    print(f'Поле отправлено, ждем других игроков')

    while True:
        resp = json.loads(await websocket.recv())['content']
        if resp == 'start_game':
            state['step'] = 'game'
            break
        else:
            print(f'Получен ответ {resp}')


async def game(websocket):
    print('Игра началась!')
    await asyncio.sleep(10)

async def handler():
    uri = "ws://localhost:8765"
    global state

    async with websockets.connect(uri, ping_interval=2, ping_timeout=2) as websocket:
        while True:
            if state['step'] == 'lobby':
                await lobby(websocket)
            elif state['step'] == 'room_wait':
                await room_wait(websocket)
            elif state['step'] == 'room_prep':
                await room_prep(websocket)
            elif state['step'] == 'game':
                await game(websocket)
            else:
                raise Exception('unknown state')

asyncio.get_event_loop().run_until_complete(handler())