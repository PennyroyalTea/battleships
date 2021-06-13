import asyncio
import json

import websockets

state = 'lobby'

async def selectRoom(websocket):
    global state

    while True:
        print('Доступные комнаты:')
        print('-' * 16)
        await websocket.send(json.dumps({'type': 'request', 'subject': 'rooms'}))
        rooms = json.loads(await websocket.recv())['content']
        for i, room in enumerate(rooms):
            print(f'Комната #{i}: {room["players"]} игроков, {"открыта" if room["state"] == "open" else "закрыта"}')
        print('-' * 16)
        while True:
            resp = input('Введите номер комнаты, чтобы присоединиться к ней. Либо "new", чтобы создать новую.')
            if resp == 'new':
                await websocket.send(json.dumps({'type': 'update', 'subject': 'rooms'}))
                break
            elif resp.isnumeric() and int(resp) < len(rooms):
                await websocket.send(json.dumps({'type': 'update', 'subject': 'connect_to_room', 'content': resp}))
                res = json.loads(await websocket.recv())
                if res['code'] == 'error':
                    print(f'Ошибка при входе в комнату: {res["content"]}')
                else:
                    state = 'room'
                    break
            else:
                print(f'Такой комнаты нет: {resp}, попробуйте снова')
                continue
        if state != 'lobby':
            break

async def handler():
    uri = "ws://localhost:8765"
    global state

    async with websockets.connect(uri) as websocket:
        while True:
            if state == 'lobby':
                room = await selectRoom(websocket)
            elif state == 'room':
                pass
            else:
                raise Exception('unknown state')

asyncio.get_event_loop().run_until_complete(handler())