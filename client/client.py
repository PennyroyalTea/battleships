import asyncio
from aioconsole import ainput
import json
import time

import websockets

state = {
    'step': 'lobby',
    'ready': False
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
            print(f'Комната #{i}: {room["players"]} игроков, {"открыта" if room["state"] == "open" else "закрыта"}')
        print('-' * 16)

        while True:
            resp = input('Введите номер комнаты, чтобы присоединиться к ней.\n '
                         'Введите "new", чтобы создать новую.\n '
                         'Введите "upd", чтобы обновить список комнат.')
            if resp == 'new':
                await websocket.send(json.dumps({'type': 'update', 'subject': 'rooms'}))
                await websocket.recv()
                break
            elif resp == 'upd':
                break
            elif resp.isnumeric() and int(resp) < len(rooms):
                await websocket.send(json.dumps({'type': 'update', 'subject': 'connect_to_room', 'content': resp}))
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


    await websocket.send(json.dumps({'type': 'request', 'subject': 'room_info'}))
    room = json.loads(await websocket.recv())['content']
    while True:

        print(f'Вы в комнате {room["name"]} [{room["ready"]} / {room["players"]}].')

        prompt = {
            True: 'Чтобы отменить готовность, введите "unready"',
            False: 'Чтобы подтвердить готовность, введите "ready"'
        }
        expected = {
            True: 'unready',
            False: 'ready'
        }

        console_task = asyncio.create_task(ainput(prompt[state['ready']]))
        recv_task = asyncio.create_task(websocket.recv())
        done, pending = await asyncio.wait(
            [console_task, recv_task],
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()
        if console_task in done:
            input = console_task.result()
            if input == expected[state['ready']]:
                if state['ready']:
                    state['ready'] = False
                    await websocket.send(json.dumps({'type': 'update', 'subject': 'ready', 'content': '-'}))
                else:
                    state['ready'] = True
                    await websocket.send(json.dumps({'type': 'update', 'subject': 'ready', 'content': '+'}))
            else:
                print(f'Некорректный ввод: {input}')
                continue
        else:
            room = json.loads(recv_task.result())['content']


async def handler():
    uri = "ws://localhost:8765"
    global state

    async with websockets.connect(uri) as websocket:
        while True:
            if state['step'] == 'lobby':
                await lobby(websocket)
            elif state['step'] == 'room_wait':
                await room_wait(websocket)
            else:
                raise Exception('unknown state')

asyncio.get_event_loop().run_until_complete(handler())