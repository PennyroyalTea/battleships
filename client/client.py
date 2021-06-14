import asyncio
from aioconsole import ainput
import json
import time
import websockets

import battleships

state = {
    'step': 'lobby',
    'field': None
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
    state['field'] = field
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
    while True:
        req = json.loads(await websocket.recv())
        my_id, msg = req['id'], json.loads(req['message'])

        if 'winner_id' in msg: # game over
            if msg['winner_id'] == my_id:
                print('Вы победили!')
            else:
                print(f'Игра закончена, победил игрок {msg["winner_id"]}')
                websocket.send(json.dumps({'type': 'update', 'subject': 'leave_game', 'content': my_id}))
                state['step'] = 'lobby'
            break

        turn, fields = msg['turn'], msg['fields']
        for i, field in enumerate(fields):
            print(f'[{i}] {"ВЫ" if my_id == i else ""}')
            battleships.print_field(field)
        print('Ваше поле:')
        battleships.print_field(state['field'])
        if my_id == turn:
            while True:
                _inp = input(f'Ваш ход! Введите через пробел номер игрока и координаты, в которые хотите выстрелить.')
                id, c = _inp.split(' ')
                if is_valid(id, c, my_id, fields):
                    await websocket.send(json.dumps({
                        'type': 'update',
                        'subject': 'shot',
                        'content': json.dumps({'to': id, 'c': c})
                    }))
                    break
                else:
                    print('Некорректный ввод')
        else:
            print(f'Ходит игрок #{turn}. Ожидайте')


def is_valid(id, c, my_id, fields):
    return id.isnumeric() and int(id) < len(fields) and int(id) != my_id \
           and len(c) == 2 and ord('A') <= ord(c[0]) <= ord('J') and 0 <= int(c[1]) <= 9

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